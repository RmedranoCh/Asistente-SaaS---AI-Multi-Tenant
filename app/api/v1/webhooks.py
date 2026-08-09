import base64
import json
from typing import Any

from fastapi import APIRouter, HTTPException, Query, status

from app.config import settings
from app.schemas.oauth import GooglePubSubWebhookIn

router = APIRouter()

DEMO_COMPANY_ID_STR = "99999999-9999-9999-9999-999999999999"


def _decode_pubsub_payload(data_b64: str) -> dict[str, Any]:
    """Decodifica y valida el payload JSON que envía Google Pub/Sub."""
    if not data_b64:
        return {}
    padded = data_b64 + "=" * (-len(data_b64) % 4)
    decoded_bytes = base64.urlsafe_b64decode(padded)
    return json.loads(decoded_bytes.decode("utf-8"))


def _enqueue_processing(company_id: str, history_id: str, user_email: str) -> None:
    # Import diferido para no arrancar el worker Celery (y su bootstrap de DB)
    # cada vez que el módulo web se importa. Solo ocurre al recibir un webhook.
    from app.workers.tasks import process_incoming_email

    process_incoming_email.delay(
        company_id_str=company_id,
        gmail_history_id=history_id,
        gmail_user_email=user_email,
    )


@router.post("/gmail", status_code=status.HTTP_200_OK)
async def google_pubsub_webhook(
    payload: GooglePubSubWebhookIn,
    token: str = Query(..., description="Token secreto para validar la procedencia de Google Cloud"),
):
    if token != settings.GOOGLE_PUBSUB_VERIFICATION_TOKEN:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token de verificación inválido.",
        )

    try:
        decoded_json = _decode_pubsub_payload(payload.message.data)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="El formato de los datos decodificados de Pub/Sub no es válido.",
        )

    email_address = decoded_json.get("emailAddress")
    history_id = decoded_json.get("historyId")

    if not email_address or not history_id:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Pub/Sub no envió emailAddress o historyId.",
        )

    _enqueue_processing(
        company_id=DEMO_COMPANY_ID_STR,
        history_id=str(history_id),
        user_email=email_address,
    )

    return {
        "status": "enqueued",
        "message": "Tarea de procesamiento cognitivo agregada a Redis.",
    }