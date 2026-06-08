import os
from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import PostgresDsn, RedisDsn, Field, ValidationInfo, field_validator

class Settings(BaseSettings):
    PROJECT_NAME: str = "Asistente SaaS AI Multi-Tenant"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"
    ENVIRONMENT: str = "development"

    ENCRYPTION_KEY: str = Field(..., validation_alias="ENCRYPTION_KEY")
    SECRET_KEY: str = Field(..., validation_alias="JWT_SECRET_KEY")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7

    DATABASE_URL: PostgresDsn = Field(..., validation_alias="DATABASE_URL")
    REDIS_URL: RedisDsn = Field(..., validation_alias="REDIS_URL")

    GOOGLE_CLIENT_ID: str = Field(..., validation_alias="GOOGLE_CLIENT_ID")
    GOOGLE_CLIENT_SECRET: str = Field(..., validation_alias="GOOGLE_CLIENT_SECRET")
    GOOGLE_PUBSUB_VERIFICATION_TOKEN: str = Field(..., validation_alias="GOOGLE_PUBSUB_VERIFICATION_TOKEN")

    GEMINI_API_KEY: str = Field(..., validation_alias="GEMINI_API_KEY")

    MOCK_GOOGLE: bool = Field(False, validation_alias="MOCK_GOOGLE")

    ALLOWED_HOSTS: List[str] = ["*"]

    @field_validator("ENCRYPTION_KEY")
    @classmethod
    def validate_encryption_key_len(cls, v: str, info: ValidationInfo) -> str:
        import base64
        try:
            decoded = base64.urlsafe_b64decode(v)
            if len(decoded) != 32:
                raise ValueError("La ENCRYPTION_KEY decodificada debe tener exactamente 32 bytes para AES-256.")
        except Exception:
            raise ValueError("La ENCRYPTION_KEY debe ser una cadena válida de tipo Fernet (32 bytes codificados en URL-safe Base64).")
        return v

    model_config = SettingsConfigDict(
        env_file=".env", 
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()