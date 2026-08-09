import pytest
from sqlalchemy import select

from app.core.tools.mock_calendar import mock_calendar_tool
from app.core.tools.mock_crm import mock_crm_tool
from app.core.tools.mock_gmail import mock_gmail_tool
from app.db.models import (
    MockCalendarEvent,
    MockCrmActivity,
    MockSentEmail,
)


@pytest.fixture(autouse=True)
def _use_test_session(session_factory, monkeypatch):
    """Redirige async_session_maker de las herramientas mock a la BD sqlite."""
    monkeypatch.setattr(
        "app.db.session.async_session_maker", session_factory
    )
    monkeypatch.setattr(
        "app.core.tools.mock_gmail.async_session_maker", session_factory
    )
    monkeypatch.setattr(
        "app.core.tools.mock_calendar.async_session_maker", session_factory
    )
    monkeypatch.setattr(
        "app.core.tools.mock_crm.async_session_maker", session_factory
    )


class TestMockGmailTool:
    async def test_access_token_is_mock(self):
        assert await mock_gmail_tool._get_access_token("x") == "mock_access_token"

    async def test_fetch_email_details_missing_returns_empty(self):
        email = await mock_gmail_tool.fetch_email_details("no-existe")
        assert email["payload"] == {}
        assert "no encontrado" in email["snippet"]

    async def test_send_email_reply_creates_record(self, session_factory):
        await mock_gmail_tool.send_email_reply(
            original_message_id="msg-1",
            thread_id="thread-1",
            to_email="to@x.com",
            subject="Re: prueba",
            body_text="Hola",
        )
        async with session_factory() as db:
            sent = (await db.execute(select(MockSentEmail))).scalars().all()
        assert len(sent) == 1
        assert sent[0].to_email == "to@x.com"
        assert sent[0].company_id is None  # arreglado: ya no usa uuid aleatorio falto de FK


class TestMockCalendarTool:
    async def test_create_meeting_persists(self, session_factory):
        result = await mock_calendar_tool.create_meeting(
            summary="Reunión",
            description="Desc",
            start_iso="2026-01-01T10:00:00Z",
            end_iso="2026-01-01T11:00:00Z",
            attendee_email="c@x.com",
        )
        assert result["id"].startswith("mock_event_")
        async with session_factory() as db:
            events = (await db.execute(select(MockCalendarEvent))).scalars().all()
        assert len(events) == 1
        assert events[0].summary == "Reunión"
        assert events[0].attendee_email == "c@x.com"


class TestMockCRMTool:
    async def test_upsert_contact_activity_persists(self, session_factory):
        result = await mock_crm_tool.upsert_contact_activity(
            api_url=None,
            api_key=None,
            email="cliente@x.com",
            activity_type="meeting_scheduled",
            notes="Cita agendada",
        )
        assert result["status"] == "success"
        async with session_factory() as db:
            acts = (await db.execute(select(MockCrmActivity))).scalars().all()
        assert len(acts) == 1
        assert acts[0].email == "cliente@x.com"
        assert acts[0].activity_type == "meeting_scheduled"