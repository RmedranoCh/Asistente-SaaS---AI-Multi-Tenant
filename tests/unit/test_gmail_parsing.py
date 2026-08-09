import base64

from app.core.tools.gmail_actions import (
    _b64decode_str,
    _strip_html,
    decode_gmail_body,
    parse_raw_email_message,
)


def _b64(text: str) -> str:
    return base64.urlsafe_b64encode(text.encode()).decode()


class TestDecodeGmailBody:
    def test_plain_text(self):
        payload = {"mimeType": "text/plain", "body": {"data": _b64("Hola mundo")}}
        assert decode_gmail_body(payload) == "Hola mundo"

    def test_html_is_stripped(self):
        payload = {
            "mimeType": "text/html",
            "body": {"data": _b64("<p>Hola <b>mundo</b></p>")},
        }
        assert "Hola mundo" in decode_gmail_body(payload)

    def test_nested_multipart_uses_text_plain(self):
        payload = {
            "mimeType": "multipart/mixed",
            "parts": [
                {
                    "mimeType": "multipart/alternative",
                    "parts": [
                        {"mimeType": "text/plain", "body": {"data": _b64("version text")}},
                        {"mimeType": "text/html", "body": {"data": _b64("<p>version html</p>")}},
                    ],
                }
            ],
        }
        assert decode_gmail_body(payload) == "version text"

    def test_empty_payload(self):
        assert decode_gmail_body({}) == ""
        assert decode_gmail_body(None) == ""

    def test_unknown_mime_returns_empty(self):
        payload = {"mimeType": "application/pdf", "body": {"data": _b64("x")}}
        assert decode_gmail_body(payload) == ""


class TestParseRawEmailMessage:
    def test_basic(self):
        raw = "From: Cliente <cliente@example.com>\r\nTo: yo@empresa.com\r\nSubject: Hola\r\nDate: Tue, 1 Jan 2026 12:00:00 +0000\r\n\r\nCuerpo"
        encoded = base64.urlsafe_b64encode(raw.encode()).decode()
        parsed = parse_raw_email_message(encoded)
        assert parsed["from"] == "Cliente <cliente@example.com>"
        assert parsed["to"] == "yo@empresa.com"
        assert parsed["subject"] == "Hola"

    def test_invalid_base64_returns_empty(self):
        assert parse_raw_email_message("!!!no-base64!!!") == {
            "from": "",
            "to": "",
            "subject": "",
            "date": "",
        }


class TestB64DecodeStr:
    def test_handles_unpadded_input(self):
        data = _b64("hola")  # url-safe ya incluye padding correcto
        assert _b64decode_str(data) == "hola"

    def test_invalid_returns_empty(self):
        assert _b64decode_str("!!!!") == ""


class TestStripHtml:
    def test_removes_tags_scripts_and_styles(self):
        html = (
            "<style>.x{color:red}</style><script>alert(1)</script>"
            "<p>Hola<br>mundo</p>"
        )
        out = _strip_html(html)
        assert "color" not in out
        assert "alert" not in out
        assert "Hola" in out and "mundo" in out
