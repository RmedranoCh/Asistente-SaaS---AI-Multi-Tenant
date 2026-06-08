import base64
import re
from email.mime.text import MIMEText
from email import message_from_bytes
from typing import Dict, Any, Optional

import httpx

from app.db.security import encryptor


class GmailActionsTool:
    GMAIL_API_BASE = "https://gmail.googleapis.com/gmail/v1/users/me"

    def __init__(self):
        self.token_url = "https://oauth2.googleapis.com/token"
        self.gmail_base_url = self.GMAIL_API_BASE

    async def _get_access_token(
        self,
        encrypted_refresh_token: str,
        client_id: str,
        client_secret: str,
    ) -> str:
        refresh_token = encryptor.decrypt_token(encrypted_refresh_token)
        payload = {
            "client_id": client_id,
            "client_secret": client_secret,
            "refresh_token": refresh_token,
            "grant_type": "refresh_token",
        }
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.post(self.token_url, data=payload)
            response.raise_for_status()
            data = response.json()
            if "access_token" not in data:
                raise RuntimeError(f"Google no devolvió access_token: {data}")
            return data["access_token"]

    async def fetch_email_details(
        self,
        message_id: str,
        encrypted_refresh_token: str,
        client_id: str,
        client_secret: str,
        format: str = "full",
    ) -> Dict[str, Any]:
        access_token = await self._get_access_token(
            encrypted_refresh_token, client_id, client_secret
        )
        headers = {"Authorization": f"Bearer {access_token}"}

        async with httpx.AsyncClient(timeout=20.0) as client:
            url = f"{self.gmail_base_url}/messages/{message_id}?format={format}"
            response = await client.get(url, headers=headers)
            response.raise_for_status()
            return response.json()

    async def list_history_messages(
        self,
        start_history_id: str,
        encrypted_refresh_token: str,
        client_id: str,
        client_secret: str,
    ) -> list:
        access_token = await self._get_access_token(
            encrypted_refresh_token, client_id, client_secret
        )
        headers = {"Authorization": f"Bearer {access_token}"}
        collected: list = []
        page_token: Optional[str] = None

        async with httpx.AsyncClient(timeout=20.0) as client:
            while True:
                params = {"startHistoryId": start_history_id, "historyTypes": "messageAdded"}
                if page_token:
                    params["pageToken"] = page_token
                resp = await client.get(
                    f"{self.gmail_base_url}/history",
                    headers=headers,
                    params=params,
                )
                resp.raise_for_status()
                data = resp.json()

                for record in data.get("history", []):
                    for added in record.get("messagesAdded", []):
                        msg = added.get("message", {})
                        if msg.get("id"):
                            collected.append(msg["id"])

                page_token = data.get("nextPageToken")
                if not page_token:
                    break

        return collected

    async def send_email_reply(
        self,
        original_message_id: str,
        thread_id: str,
        to_email: str,
        subject: str,
        body_text: str,
        encrypted_refresh_token: str,
        client_id: str,
        client_secret: str,
    ) -> Dict[str, Any]:
        access_token = await self._get_access_token(
            encrypted_refresh_token, client_id, client_secret
        )
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }

        message = MIMEText(body_text, _charset="utf-8")
        message["to"] = to_email
        message["subject"] = subject if subject.lower().startswith("re:") else f"Re: {subject}"
        if original_message_id:
            message["In-Reply-To"] = original_message_id
            message["References"] = original_message_id

        raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode()
        payload: Dict[str, Any] = {"raw": raw_message}
        if thread_id:
            payload["threadId"] = thread_id

        async with httpx.AsyncClient(timeout=20.0) as client:
            url = f"{self.gmail_base_url}/messages/send"
            response = await client.post(url, json=payload, headers=headers)
            response.raise_for_status()
            return response.json()


def decode_gmail_body(payload: Dict[str, Any]) -> str:
    if not payload:
        return ""

    def _walk(part: Dict[str, Any]) -> Optional[str]:
        mime_type = part.get("mimeType", "")
        if mime_type == "text/plain" and part.get("body", {}).get("data"):
            return _b64decode_str(part["body"]["data"])
        if mime_type == "text/html" and part.get("body", {}).get("data"):
            html = _b64decode_str(part["body"]["data"])
            return _strip_html(html)
        for sub in part.get("parts", []) or []:
            result = _walk(sub)
            if result:
                return result
        return None

    decoded = _walk(payload)
    if decoded:
        return decoded.strip()
    return ""


def _b64decode_str(data: str) -> str:
    padded = data + "=" * (-len(data) % 4)
    try:
        return base64.urlsafe_b64decode(padded).decode("utf-8", errors="replace")
    except Exception:
        return ""


def _strip_html(html: str) -> str:
    text = re.sub(r"<style[^>]*>.*?</style>", " ", html, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<script[^>]*>.*?</script>", " ", text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<br\s*/?>", "\n", text, flags=re.IGNORECASE)
    text = re.sub(r"</p>", "\n", text, flags=re.IGNORECASE)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text


def parse_raw_email_message(raw_b64: str) -> Dict[str, str]:
    padded = raw_b64 + "=" * (-len(raw_b64) % 4)
    try:
        raw_bytes = base64.urlsafe_b64decode(padded)
        msg = message_from_bytes(raw_bytes)
        return {
            "from": msg.get("From", ""),
            "to": msg.get("To", ""),
            "subject": msg.get("Subject", ""),
            "date": msg.get("Date", ""),
        }
    except Exception:
        return {"from": "", "to": "", "subject": "", "date": ""}


gmail_tool = GmailActionsTool()
