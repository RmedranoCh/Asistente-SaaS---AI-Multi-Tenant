import uuid
import httpx
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.config import settings
from app.db.session import get_db
from app.db.models import GoogleCredential
from app.db.security import encryptor
from app.schemas.oauth import GoogleAuthCodeIn, TenantCredentialsResponse

router = APIRouter()

DEMO_COMPANY_ID = uuid.UUID("99999999-9999-9999-9999-999999999999")

GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v2/userinfo"


@router.post("/connect-gmail", response_model=TenantCredentialsResponse)
async def connect_gmail_account(
    payload: GoogleAuthCodeIn,
    db: AsyncSession = Depends(get_db),
):
    data_payload = {
        "code": payload.code,
        "client_id": settings.GOOGLE_CLIENT_ID,
        "client_secret": settings.GOOGLE_CLIENT_SECRET,
        "redirect_uri": "postmessage",
        "grant_type": "authorization_code",
    }

    async with httpx.AsyncClient(timeout=15.0) as client:
        token_response = await client.post(GOOGLE_TOKEN_URL, data=data_payload)
        if token_response.status_code != 200:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"No se pudo validar el código de autorización con Google: {token_response.text}",
            )

        tokens = token_response.json()
        refresh_token = tokens.get("refresh_token")
        access_token = tokens.get("access_token")

        if not refresh_token:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    "Google no devolvió un Refresh Token. "
                    "Asegúrate de enviar prompt=consent y access_type=offline, "
                    "luego revoca los accesos del SaaS en tu cuenta e intenta de nuevo."
                ),
            )

        headers = {"Authorization": f"Bearer {access_token}"}
        user_response = await client.get(GOOGLE_USERINFO_URL, headers=headers)
        if user_response.status_code != 200:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No se pudo obtener la información del usuario de Google.",
            )
        user_email = user_response.json().get("email")

        if not user_email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="La respuesta de Google no incluyó el email del usuario.",
            )

    encrypted_token = encryptor.encrypt_token(refresh_token)

    query = select(GoogleCredential).where(GoogleCredential.company_id == DEMO_COMPANY_ID)
    result = await db.execute(query)
    db_credential = result.scalar_one_or_none()

    if db_credential:
        db_credential.email_address = user_email
        db_credential.encrypted_refresh_token = encrypted_token
        db_credential.is_active = True
    else:
        db_credential = GoogleCredential(
            company_id=DEMO_COMPANY_ID,
            email_address=user_email,
            encrypted_refresh_token=encrypted_token,
            is_active=True,
        )
        db.add(db_credential)

    await db.commit()
    await db.refresh(db_credential)

    return db_credential
