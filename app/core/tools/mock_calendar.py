import uuid
from datetime import datetime, timezone
from typing import Dict, Any
from app.db.session import async_session_maker
from app.db.models import MockCalendarEvent


class MockGoogleCalendarTool:
    async def create_meeting(
        self,
        summary: str,
        description: str,
        start_iso: str,
        end_iso: str,
        attendee_email: str,
        **kwargs,
    ) -> Dict[str, Any]:
        event_id = f"mock_event_{uuid.uuid4().hex[:12]}"
        async with async_session_maker() as db:
            event = MockCalendarEvent(
                summary=summary,
                description=description,
                start_iso=start_iso,
                end_iso=end_iso,
                attendee_email=attendee_email,
                event_id=event_id,
                html_link=f"https://calendar.google.com/mock/{event_id}",
            )
            db.add(event)
            await db.commit()
            await db.refresh(event)

        return {
            "id": event_id,
            "summary": summary,
            "htmlLink": event.html_link,
            "start": {"dateTime": start_iso, "timeZone": "UTC"},
            "end": {"dateTime": end_iso, "timeZone": "UTC"},
            "attendees": [{"email": attendee_email}],
        }


mock_calendar_tool = MockGoogleCalendarTool()
