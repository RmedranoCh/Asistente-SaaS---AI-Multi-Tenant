import base64
import json

from app.api.v1 import webhooks
from app.config import settings


def _encode_pubsub_data(email_address, history_id):
    payload = json.dumps({"emailAddress": email_address, "historyId": history_id})
    return base64.urlsafe_b64encode(payload.encode()).decode()


def _valid_body(data: str) -> dict:
    return {
        "message": {
            "data": data,
            "messageId": "msg-1",
            "publishTime": "2026-01-01T00:00:00.000Z",
        },
        "subscription": "projects/x/subscriptions/y",
    }


class TestWebhookAuth:
    async def test_wrong_token_rejected(self, client):
        resp = await client.post(
            "/api/v1/webhooks/gmail",
            params={"token": "bad-token"},
            json=_valid_body(_encode_pubsub_data("a@b.c", history_id=1)),
        )
        assert resp.status_code == 401

    async def test_invalid_base64_payload_rejected(self, client):
        resp = await client.post(
            "/api/v1/webhooks/gmail",
            params={"token": settings.GOOGLE_PUBSUB_VERIFICATION_TOKEN},
            json=_valid_body("!!!invalid!!!x"),
        )
        assert resp.status_code == 422

    async def test_missing_email_or_history_rejected(self, client):
        payload = base64.urlsafe_b64encode(b'{"something": "else"}').decode()
        resp = await client.post(
            "/api/v1/webhooks/gmail",
            params={"token": settings.GOOGLE_PUBSUB_VERIFICATION_TOKEN},
            json=_valid_body(payload),
        )
        assert resp.status_code == 422


class TestWebhookProcessing:
    async def test_valid_webhook_calls_enqueue(self, client, monkeypatch):
        captured = {}

        def fake_enqueue(company_id, history_id, user_email):
            captured.update(
                {
                    "company_id": company_id,
                    "history_id": history_id,
                    "user_email": user_email,
                }
            )

        monkeypatch.setattr(webhooks, "_enqueue_processing", fake_enqueue)

        data = _encode_pubsub_data("cliente@example.com", history_id=123)
        resp = await client.post(
            "/api/v1/webhooks/gmail",
            params={"token": settings.GOOGLE_PUBSUB_VERIFICATION_TOKEN},
            json=_valid_body(data),
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "enqueued"
        assert captured["company_id"] == "99999999-9999-9999-9999-999999999999"
        assert captured["history_id"] == "123"
        assert captured["user_email"] == "cliente@example.com"