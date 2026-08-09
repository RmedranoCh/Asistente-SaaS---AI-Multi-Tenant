import uuid

from sqlalchemy import select

from app.db.models import (
    Company,
    GoogleCredential,
)

DEMO_COMPANY_ID = "99999999-9999-9999-9999-999999999999"
DEMO_COMPANY_UUID = uuid.UUID(DEMO_COMPANY_ID)


class TestSeed:
    async def test_seed_creates_demo_data(self, client):
        resp = await client.post("/api/v1/mock/seed")
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "ok"
        assert body["company_id"] == DEMO_COMPANY_ID
        assert len(body["mock_emails"]) == 4

    async def test_seed_is_idempotent(self, client):
        await client.post("/api/v1/mock/seed")
        resp = await client.post("/api/v1/mock/seed")
        assert resp.status_code == 200
        assert "ya existen" in resp.json()["message"]

    async def test_seed_creates_company_and_credential(self, client, session_factory):
        await client.post("/api/v1/mock/seed")
        async with session_factory() as db:
            company = await db.get(Company, DEMO_COMPANY_UUID)
            cred_result = await db.execute(
                select(GoogleCredential).where(
                    GoogleCredential.company_id == company.id
                )
            )
            cred = cred_result.scalar_one_or_none()
        assert company is not None
        assert company.name == "Demo Company (Mock)"
        assert cred is not None and cred.is_active is True


class TestInbox:
    async def test_empty_before_seed(self, client):
        resp = await client.get("/api/v1/mock/inbox")
        assert resp.status_code == 200
        assert resp.json()["count"] == 0

    async def test_returns_seeded_emails(self, client):
        await client.post("/api/v1/mock/seed")
        resp = await client.get("/api/v1/mock/inbox")
        assert resp.status_code == 200
        body = resp.json()
        assert body["count"] == 4
        subjects = {e["subject"] for e in body["emails"]}
        assert "Consulta sobre horarios de atención" in subjects


class TestSentEventsCrm:
    async def test_sent_events_crm_empty_by_default(self, client):
        for path in ("/api/v1/mock/sent", "/api/v1/mock/events", "/api/v1/mock/crm"):
            resp = await client.get(path)
            assert resp.status_code == 200
            assert resp.json()["count"] == 0

    async def test_crm_listing_shape(self, client):
        await client.post("/api/v1/mock/seed")
        resp = await client.get("/api/v1/mock/crm")
        body = resp.json()
        assert "activities" in body


class TestReset:
    async def test_reset_clears_all_mock_tables(self, client):
        await client.post("/api/v1/mock/seed")
        resp = await client.post("/api/v1/mock/reset")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"

        for path in ("/api/v1/mock/inbox", "/api/v1/mock/sent", "/api/v1/mock/events", "/api/v1/mock/crm"):
            r = await client.get(path)
            assert r.json()["count"] == 0
