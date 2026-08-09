from app.db.security import TokenEncryptor, encryptor


class TestTokenEncryptor:
    def test_round_trip(self):
        raw = "refresh_token_super_secreto"
        encrypted = encryptor.encrypt_token(raw)
        assert encrypted != raw
        assert encryptor.decrypt_token(encrypted) == raw

    def test_encrypt_empty_returns_empty(self):
        assert encryptor.encrypt_token("") == ""

    def test_decrypt_empty_returns_empty(self):
        assert encryptor.decrypt_token("") == ""

    def test_encrypt_is_reversible_and_randomized(self):
        raw = "abc123"
        enc1 = encryptor.encrypt_token(raw)
        enc2 = encryptor.encrypt_token(raw)
        assert enc1 != enc2  # Fernet usa IV aleatorio
        assert encryptor.decrypt_token(enc1) == encryptor.decrypt_token(enc2) == raw

    def test_decrypt_tampered_token_raises(self):
        import pytest
        from cryptography.fernet import InvalidToken

        encrypted = encryptor.encrypt_token("secret")
        tampered = "A" + encrypted[1:]
        with pytest.raises(InvalidToken):
            encryptor.decrypt_token(tampered)

    def test_tokens_interchangeable_with_fresh_instance(self):
        # Un token cifrado con el singleton debe poder descifrarse con otra
        # instancia que usa la misma ENCRYPTION_KEY (compatibilidad multi-proceso).
        raw = "refresh_token"
        encrypted = encryptor.encrypt_token(raw)
        fresh = TokenEncryptor()
        assert fresh.decrypt_token(encrypted) == raw
        assert encryptor.fernet is not fresh.fernet
