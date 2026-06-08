from datetime import datetime, timezone
from typing import Dict, Any, Optional
from app.db.session import async_session_maker
from app.db.models import MockCrmActivity


class MockCRMIntegrationTool:
    async def upsert_contact_activity(
        self,
        api_url: Optional[str],
        api_key: Optional[str],
        email: str,
        activity_type: str,
        notes: str,
    ) -> Dict[str, Any]:
        async with async_session_maker() as db:
            activity = MockCrmActivity(
                email=email,
                activity_type=activity_type,
                notes=notes,
            )
            db.add(activity)
            await db.commit()
            await db.refresh(activity)

        return {
            "status": "success",
            "crm_response": {
                "id": str(activity.id),
                "contact_email": email,
                "activity": {
                    "type": activity_type,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "description": notes,
                },
            },
        }


mock_crm_tool = MockCRMIntegrationTool()
