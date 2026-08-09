import base64

import pytest
from pydantic import ValidationError

from app.config import Settings


class TestSettingsValidation:
    def test_valid_encryption_key_32_bytes_accepted(self):
        key = base64.urlsafe_b64encode(b"a" * 32).decode()
        settings = Settings(ENCRYPTION_KEY=key)
        assert settings.ENCRYPTION_KEY == key

    def test_short_encryption_key_rejected(self):
        key = base64.urlsafe_b64encode(b"short-key").decode()
        with pytest.raises(ValidationError):
            Settings(ENCRYPTION_KEY=key)

    def test_invalid_base64_rejected(self):
        with pytest.raises(ValidationError):
            Settings(ENCRYPTION_KEY="not-valid-base64!!!")


class TestSettingsEnvRead:
    def test_mock_mode_default_matches_env(self):
        settings = Settings()
        assert settings.MOCK_GOOGLE is True
        assert settings.API_V1_STR == "/api/v1"
        assert settings.PROJECT_NAME