import httpx
from typing import Dict, Any
from app.core.tools.gmail_actions import gmail_tool


class GoogleCalendarTool:
    def __init__(self):
        self.calendar_base_url = "https://www.googleapis.com/calendar/v3/calendars/primary/events"

    async def create_meeting(
        self,
        summary: str,
        description: str,
        start_iso: str,
        end_iso: str,
        attendee_email: str,
        encrypted_refresh_token: str,
        client_id: str,
        client_secret: str,
        time_zone: str = "UTC",
    ) -> Dict[str, Any]:
        access_token = await gmail_tool._get_access_token(
            encrypted_refresh_token, client_id, client_secret
        )
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }

        event_payload = {
            "summary": summary,
            "description": description,
            "start": {"dateTime": start_iso, "timeZone": time_zone},
            "end": {"dateTime": end_iso, "timeZone": time_zone},
            "attendees": [{"email": attendee_email}],
            "reminders": {"useDefault": True},
        }

        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.post(
                self.calendar_base_url, json=event_payload, headers=headers
            )
            response.raise_for_status()
            return response.json()


calendar_tool = GoogleCalendarTool()
