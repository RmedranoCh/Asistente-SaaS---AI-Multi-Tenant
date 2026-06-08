import json
import re
import uuid
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional

from google import genai
from google.genai import types
from sqlalchemy import select

from app.config import settings
from app.core.agents.states import EmailAgentState
from app.core.rag.engine import rag_engine
from app.core.tools import calendar_tool, crm_tool
from app.db.models import GoogleCredential
from app.db.session import async_session_maker

ai_client = genai.Client(api_key=settings.GEMINI_API_KEY)


def _safe_json(text: str) -> Dict[str, Any]:
    text = (text or "").strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?", "", text).strip()
        text = re.sub(r"```$", "", text).strip()
    try:
        return json.loads(text)
    except Exception:
        return {}


def node_classify_email(state: EmailAgentState) -> EmailAgentState:
    prompt = f"""
    Analiza el siguiente correo electrónico corporativo y clasifícalo estrictamente en una de estas 4 categorías:
    - 'Duda': Preguntas sobre el servicio, horarios, características o información general.
    - 'Cita': Solicitudes para agendar, cancelar o reprogramar reuniones.
    - 'Reembolso': Peticiones de devolución de dinero o disputas de pago.
    - 'Queja': Reclamos por mal servicio, fallos técnicos o inconformidades.

    Responde ÚNICAMENTE con un objeto JSON válido con la estructura: {{"intent": "CATEGORIA"}}

    Asunto: {state.get('subject', '')}
    Cuerpo: {state.get('body', '')}
    """

    try:
        response = ai_client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                temperature=0.0,
            ),
        )
        data = _safe_json(response.text)
        intent = data.get("intent", "Queja")
        if intent not in ("Duda", "Cita", "Reembolso", "Queja"):
            intent = "Queja"
        state["intent"] = intent
    except Exception:
        state["intent"] = "Queja"
    return state


def node_enrich_rag(state: EmailAgentState) -> EmailAgentState:
    if state.get("intent") == "Duda":
        context = rag_engine.query_tenant_knowledge(
            company_id=state.get("company_id", ""),
            query_text=state.get("body", ""),
        )
        state["rag_context"] = context
    else:
        state["rag_context"] = ""
    return state


def node_decision_and_draft(state: EmailAgentState) -> EmailAgentState:
    intent = state.get("intent")

    if intent in ("Reembolso", "Queja"):
        state["requires_approval"] = True
    else:
        state["requires_approval"] = False

    system_instruction = (
        "Eres un asistente virtual de atención al cliente altamente profesional, conciso y empático. "
        "Responde en español neutro. No inventes datos."
    )
    if state.get("rag_context"):
        system_instruction += (
            "\nUsa estrictamente esta información interna validada de la empresa para responder:\n"
            f"{state['rag_context']}"
        )

    prompt = f"""
    Genera una respuesta de correo electrónico óptima y profesional para el cliente.
    Remitente: {state.get('sender', '')}
    Asunto Original: {state.get('subject', '')}
    Correo recibido: {state.get('body', '')}
    Categoría: {intent}

    Escribe directamente el cuerpo del correo listo para ser enviado, manteniendo un tono corporativo excelente.
    """

    try:
        response = ai_client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction=system_instruction,
                temperature=0.3,
            ),
        )
        state["suggested_reply"] = (response.text or "").strip()
    except Exception as e:
        state["suggested_reply"] = (
            "Lo sentimos, estamos procesando su solicitud internamente y "
            "nos comunicaremos a la brevedad."
        )
        state["requires_approval"] = True
        state["tool_error"] = f"draft_error: {str(e)[:200]}"

    return state


def _extract_email_address(sender: str) -> str:
    match = re.search(r"<([^>]+)>", sender or "")
    if match:
        return match.group(1).strip()
    return (sender or "").strip()


async def _extract_meeting_details(state: EmailAgentState) -> Optional[Dict[str, Any]]:
    prompt = f"""
    Analiza el siguiente correo y determina si el cliente propone una reunión.
    Si la hay, devuelve un JSON con:
      {{
        "summary": "título corto de la reunión",
        "description": "breve descripción",
        "start_iso": "fecha y hora ISO 8601 en UTC (YYYY-MM-DDTHH:MM:SSZ)",
        "end_iso": "fecha y hora ISO 8601 en UTC (YYYY-MM-DDTHH:MM:SSZ)",
        "duration_minutes": número entero
      }}
    Si NO hay una reunión clara, devuelve exactamente: {{"meeting": null}}

    Correo:
    Asunto: {state.get('subject', '')}
    Cuerpo: {state.get('body', '')}
    """

    try:
        response = ai_client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                temperature=0.0,
            ),
        )
        data = _safe_json(response.text)
    except Exception:
        return None

    if not data or data.get("meeting") is None or not data.get("start_iso"):
        return None

    try:
        start = datetime.fromisoformat(data["start_iso"].replace("Z", "+00:00"))
    except Exception:
        return None

    if start.tzinfo is None:
        start = start.replace(tzinfo=timezone.utc)

    duration = int(data.get("duration_minutes") or 30)
    end = start + timedelta(minutes=duration)
    data["start_iso"] = start.strftime("%Y-%m-%dT%H:%M:%SZ")
    data["end_iso"] = end.strftime("%Y-%m-%dT%H:%M:%SZ")
    return data


async def _get_company_credentials(company_id_str: str) -> Optional[GoogleCredential]:
    try:
        cid = uuid.UUID(company_id_str)
    except Exception:
        return None
    async with async_session_maker() as db:
        result = await db.execute(
            select(GoogleCredential).where(GoogleCredential.company_id == cid)
        )
        return result.scalar_one_or_none()


async def node_execute_actions(state: EmailAgentState) -> EmailAgentState:
    actions: List[Dict[str, Any]] = list(state.get("actions_taken") or [])

    if state.get("intent") != "Cita":
        state["actions_taken"] = actions
        return state

    credentials = await _get_company_credentials(state.get("company_id", ""))
    if not credentials or not credentials.is_active:
        state["actions_taken"] = actions
        return state

    meeting = await _extract_meeting_details(state)
    if not meeting:
        state["actions_taken"] = actions
        return state

    try:
        attendee = _extract_email_address(state.get("sender", ""))
        calendar_resp = await calendar_tool.create_meeting(
            summary=meeting.get("summary") or "Reunión con el cliente",
            description=meeting.get("description") or state.get("body", ""),
            start_iso=meeting["start_iso"],
            end_iso=meeting["end_iso"],
            attendee_email=attendee,
            encrypted_refresh_token=credentials.encrypted_refresh_token,
            client_id=settings.GOOGLE_CLIENT_ID,
            client_secret=settings.GOOGLE_CLIENT_SECRET,
        )
        actions.append(
            {
                "tool": "google_calendar",
                "status": "success",
                "event_id": calendar_resp.get("id"),
                "html_link": calendar_resp.get("htmlLink"),
            }
        )
    except Exception as e:
        actions.append(
            {"tool": "google_calendar", "status": "error", "message": str(e)[:200]}
        )
        state["requires_approval"] = True
        state["tool_error"] = f"calendar_error: {str(e)[:200]}"

    try:
        crm_resp = await crm_tool.upsert_contact_activity(
            api_url=None,
            api_key=None,
            email=_extract_email_address(state.get("sender", "")),
            activity_type="meeting_scheduled",
            notes=f"Cita agendada: {meeting.get('summary', '')} el {meeting['start_iso']}",
        )
        actions.append({"tool": "crm", **crm_resp})
    except Exception as e:
        actions.append({"tool": "crm", "status": "error", "message": str(e)[:200]})

    state["actions_taken"] = actions
    return state
