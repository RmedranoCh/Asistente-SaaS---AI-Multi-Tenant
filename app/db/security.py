import base64
from cryptography.fernet import Fernet
from app.config import settings

class TokenEncryptor:
    def __init__(self):
        self.fernet = Fernet(settings.ENCRYPTION_KEY.encode())

    def encrypt_token(self, raw_token: str) -> str:
        if not raw_token:
            return ""
        return self.fernet.encrypt(raw_token.encode()).decode()

    def decrypt_token(self, encrypted_token: str) -> str:
        if not encrypted_token:
            return ""
        return self.fernet.decrypt(encrypted_token.encode()).decode()

encryptor = TokenEncryptor()