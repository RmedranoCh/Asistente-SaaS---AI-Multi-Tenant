import uuid
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, EmailStr, Field

class GoogleAuthCodeIn(BaseModel):
    code: str = Field(..., description="El Authorization Code devuelto por Google en la redirección.")
    state: Optional[str] = Field(None, description="Parámetro de seguridad para prevenir ataques CSRF.")

class TenantCredentialsCreate(BaseModel):
    company_id: uuid.UUID
    email_address: EmailStr
    encrypted_refresh_token: str

class TenantCredentialsResponse(BaseModel):
    company_id: uuid.UUID
    email_address: EmailStr
    is_active: bool

    class Config:
        from_attributes = True

class PubSubMessage(BaseModel) :
    data: str = Field(..., description="Datos del evento (información del buzón) cifrados en Base64.")
    message_id: str = Field(..., alias="messageId")
    publish_time: str = Field(..., alias="publishTime")
    attributes: Optional[Dict[str, str]] = Field(None, description="Atributos extra de metadata enviados por Google.")

class GooglePubSubWebhookIn(BaseModel):
    message: PubSubMessage
    subscription: str = Field(..., description="El nombre del recurso de suscripción que disparó el webhook.")