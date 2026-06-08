import uuid
from datetime import datetime
from typing import Dict, Any, Optional, List
from sqlalchemy import select
from app.db.session import async_session_maker
from app.db.models import MockInboxEmail, MockSentEmail


class MockGmailActionsTool:
    async def _get_access_token(self, *args, **kwargs) -> str:
        return "mock_access_token"

    async def list_history_messages(
        self,
        start_history_id: str,
        **kwargs,
    ) -> list:
        async with async_session_maker() as db:
            result = await db.execute(
                select(MockInboxEmail).where(
                    MockInboxEmail.history_id >= start_history_id,
                    MockInboxEmail.is_processed == False,
                )
            )
            emails = result.scalars().all()
            return [e.gmail_message_id for e in emails]

    async def fetch_email_details(
        self,
        message_id: str,
        **kwargs,
    ) -> Dict[str, Any]:
        async with async_session_maker() as db:
            result = await db.execute(
                select(MockInboxEmail).where(
                    MockInboxEmail.gmail_message_id == message_id
                )
            )
            email = result.scalar_one_or_none()

        if not email:
            return {"payload": {}, "snippet": "(correo simulado no encontrado)"}

        return {
            "id": email.gmail_message_id,
            "threadId": email.gmail_thread_id or email.gmail_message_id,
            "payload": {
                "headers": [
                    {"name": "From", "value": email.sender},
                    {"name": "Subject", "value": email.subject},
                ],
                "mimeType": "text/plain",
                "body": {"data": _encode_b64(email.body_content)},
            },
            "snippet": email.body_content[:120],
            "internalDate": str(int(email.created_at.timestamp() * 1000)),
        }

    async def send_email_reply(
        self,
        original_message_id: str,
        thread_id: str,
        to_email: str,
        subject: str,
        body_text: str,
        encrypted_refresh_token: str = "",
        **kwargs,
    ) -> Dict[str, Any]:
        mock_id = str(uuid.uuid4())
        async with async_session_maker() as db:
            sent = MockSentEmail(
                company_id=uuid.uuid(),  # se sobreescribe abajo si hay contexto
                original_message_id=original_message_id,
                thread_id=thread_id,
                to_email=to_email,
                subject=subject,
                body_text=body_text,
            )
            db.add(sent)
            await db.commit()
            await db.refresh(sent)

        return {
            "id": mock_id,
            "threadId": thread_id,
            "labelIds": ["SENT"],
            "payload": {"headers": [{"name": "To", "value": to_email}]},
        }


def _encode_b64(text: str) -> str:
    import base64
    return base64.urlsafe_b64encode(text.encode("utf-8")).decode()


mock_gmail_tool = MockGmailActionsTool()
