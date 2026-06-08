import asyncio
import uuid
from datetime import datetime
from sqlalchemy import select

from app.workers.worker import celery_app
from app.db.session import async_session_maker
from app.db.models import EmailLog, GoogleCredential
from app.config import settings
from app.core.tools import gmail_tool
from app.core.tools.gmail_actions import decode_gmail_body
from app.core.agents.graph import email_cognitive_graph


@celery_app.task(
    name="tasks.process_incoming_email",
    max_retries=3,
    default_retry_delay=15,
    autoretry_for=(Exception,),
    retry_backoff=True,
)
def process_incoming_email(company_id_str: str, gmail_history_id: str, gmail_user_email: str):
    return asyncio.run(
        _async_process_incoming_email(company_id_str, gmail_history_id, gmail_user_email)
    )


async def _async_process_incoming_email(
    company_id_str: str, gmail_history_id: str, gmail_user_email: str
):
    company_id = uuid.UUID(company_id_str)

    async with async_session_maker() as db:
        cred_query = select(GoogleCredential).where(GoogleCredential.company_id == company_id)
        cred_result = await db.execute(cred_query)
        credentials = cred_result.scalar_one_or_none()

        if not credentials or not credentials.is_active:
            return f"Error: Credenciales no encontradas o inactivas para {company_id_str}"

        if credentials.email_address.lower() != gmail_user_email.lower():
            return f"Ignorado: el evento Pub/Sub pertenece a {gmail_user_email}, no a esta empresa."

        try:
            message_ids = await gmail_tool.list_history_messages(
                start_history_id=gmail_history_id,
                encrypted_refresh_token=credentials.encrypted_refresh_token,
                client_id=settings.GOOGLE_CLIENT_ID,
                client_secret=settings.GOOGLE_CLIENT_SECRET,
            )
        except Exception as e:
            return f"Error consultando historial de Gmail: {str(e)}"

        if not message_ids:
            return f"Sin mensajes nuevos en historyId={gmail_history_id}."

        processed = []
        for message_id in message_ids:
            existing = await db.execute(
                select(EmailLog).where(EmailLog.gmail_message_id == message_id)
            )
            if existing.scalar_one_or_none():
                continue
            try:
                outcome = await _process_single_message(
                    db=db,
                    company_id=company_id,
                    message_id=message_id,
                    credentials=credentials,
                )
                processed.append(outcome)
            except Exception as e:
                processed.append(f"Error con {message_id}: {str(e)}")

        await db.commit()
        return f"Procesados {len(processed)} mensaje(s) del historyId {gmail_history_id}."


async def _process_single_message(db, company_id, message_id, credentials):
    email_data = await gmail_tool.fetch_email_details(
        message_id=message_id,
        encrypted_refresh_token=credentials.encrypted_refresh_token,
        client_id=settings.GOOGLE_CLIENT_ID,
        client_secret=settings.GOOGLE_CLIENT_SECRET,
    )

    payload = email_data.get("payload", {}) or {}
    headers = {h["name"].lower(): h["value"] for h in payload.get("headers", [])}
    sender = headers.get("from", "Desconocido")
    subject = headers.get("subject", "(Sin Asunto)")
    thread_id = email_data.get("threadId") or None
    body = decode_gmail_body(payload) or email_data.get("snippet", "")

    email_log = EmailLog(
        company_id=company_id,
        gmail_message_id=message_id,
        gmail_thread_id=thread_id,
        sender=sender,
        subject=subject,
        body_content=body,
        status="PROCESSING",
    )
    db.add(email_log)
    await db.flush()

    initial_state = {
        "company_id": str(company_id),
        "email_log_id": str(email_log.id),
        "sender": sender,
        "subject": subject,
        "body": body,
        "intent": None,
        "rag_context": None,
        "suggested_reply": None,
        "requires_approval": False,
        "actions_taken": [],
    }

    final_state = await email_cognitive_graph.ainvoke(initial_state)

    email_log.detected_intent = final_state.get("intent")
    email_log.suggested_reply = final_state.get("suggested_reply")
    email_log.rag_context = final_state.get("rag_context")
    email_log.actions_taken = {"events": final_state.get("actions_taken", [])}
    email_log.processed_at = datetime.utcnow()

    if final_state.get("requires_approval"):
        email_log.status = "PENDING_APPROVAL"
        email_log.requires_human_review = True
    else:
        try:
            await gmail_tool.send_email_reply(
                original_message_id=message_id,
                thread_id=thread_id or "",
                to_email=sender,
                subject=subject,
                body_text=final_state.get("suggested_reply") or "",
                encrypted_refresh_token=credentials.encrypted_refresh_token,
                client_id=settings.GOOGLE_CLIENT_ID,
                client_secret=settings.GOOGLE_CLIENT_SECRET,
            )
            email_log.status = "AUTO_SENT"
            email_log.requires_human_review = False
        except Exception as e:
            email_log.status = "PENDING_APPROVAL"
            email_log.requires_human_review = True
            email_log.suggested_reply = (
                (email_log.suggested_reply or "")
                + f"\n\n[Error de envío automático: {str(e)[:200]}]"
            ).strip()

    return f"{message_id} -> {email_log.status}"


@celery_app.task(name="tasks.send_approved_email")
def send_approved_email(email_log_id_str: str, final_reply: str = ""):
    return asyncio.run(_async_send_approved_email(email_log_id_str, final_reply))


async def _async_send_approved_email(email_log_id_str: str, final_reply: str = ""):
    email_log_id = uuid.UUID(email_log_id_str)
    async with async_session_maker() as db:
        log_query = select(EmailLog).where(EmailLog.id == email_log_id)
        log_result = await db.execute(log_query)
        email_log = log_result.scalar_one_or_none()

        if not email_log:
            return "Error: Registro de correo no encontrado."

        cred_query = select(GoogleCredential).where(
            GoogleCredential.company_id == email_log.company_id
        )
        cred_result = await db.execute(cred_query)
        credentials = cred_result.scalar_one_or_none()

        if not credentials:
            return "Error: Credenciales de la empresa no encontradas."

        body_to_send = (final_reply or email_log.approved_reply or email_log.suggested_reply or "").strip()
        if not body_to_send:
            return "Error: No hay contenido para enviar."

        try:
            await gmail_tool.send_email_reply(
                original_message_id=email_log.gmail_message_id,
                thread_id=email_log.gmail_thread_id or email_log.gmail_message_id,
                to_email=email_log.sender,
                subject=email_log.subject,
                body_text=body_to_send,
                encrypted_refresh_token=credentials.encrypted_refresh_token,
                client_id=settings.GOOGLE_CLIENT_ID,
                client_secret=settings.GOOGLE_CLIENT_SECRET,
            )
            email_log.status = "MANUALLY_APPROVED"
            email_log.approved_reply = body_to_send
            await db.commit()
        except Exception as e:
            return f"Fallo al enviar correo aprobado: {str(e)}"

    return f"Correo {email_log_id_str} enviado manualmente de forma exitosa."
