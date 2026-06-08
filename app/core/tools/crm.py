import httpx
from typing import Dict, Any, Optional
from datetime import datetime, timezone


class CRMIntegrationTool:
    async def upsert_contact_activity(
        self,
        api_url: Optional[str],
        api_key: Optional[str],
        email: str,
        activity_type: str,
        notes: str,
    ) -> Dict[str, Any]:
        if not api_url or not api_key:
            return {"status": "skipped", "reason": "CRM no configurado para este inquilino."}

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

        payload = {
            "contact_email": email,
            "activity": {
                "type": activity_type,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "description": notes,
            },
        }

        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.post(api_url, json=payload, headers=headers)
                if response.status_code in (200, 201, 202):
                    try:
                        return {"status": "success", "crm_response": response.json()}
                    except Exception:
                        return {"status": "success", "crm_response": None}
                return {
                    "status": "failed",
                    "code": response.status_code,
                    "body": response.text[:300],
                }
        except Exception as e:
            return {"status": "error", "message": str(e)}


crm_tool = CRMIntegrationTool()
