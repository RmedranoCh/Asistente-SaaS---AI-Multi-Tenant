import json
import base64
from fastapi import APIRouter, Query, HTTPException, status

from app.config import settings
from app.schemas.oauth import GooglePubSubWebhookIn
from app.workers.tasks import process_incoming_email

router = APIRouter()

DEMO_COMPANY_ID_STR = "99999999-9999-9999-9999-999999999999"


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
        padded = payload.message.data + "=" * (-len(payload.message.data) % 4)
        decoded_bytes = base64.urlsafe_b64decode(padded)
        decoded_json = json.loads(decoded_bytes.decode("utf-8"))
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

    process_incoming_email.delay(
        company_id_str=DEMO_COMPANY_ID_STR,
        gmail_history_id=str(history_id),
        gmail_user_email=email_address,
    )

    return {
        "status": "enqueued",
        "message": "Tarea de procesamiento cognitivo agregada a Redis.",
    }
