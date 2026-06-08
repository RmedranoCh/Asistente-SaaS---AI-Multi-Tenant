import uuid
from fastapi import APIRouter, Request, Depends, HTTPException, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.session import get_db
from app.db.models import GoogleCredential, EmailLog
from app.config import settings

router = APIRouter(tags=["UI Settings"])
templates = Jinja2Templates(directory="app/templates")

DEMO_COMPANY_ID = uuid.UUID("99999999-9999-9999-9999-999999999999")


@router.get("/settings", response_class=HTMLResponse)
async def settings_page(request: Request, db: AsyncSession = Depends(get_db)):
    cred_query = select(GoogleCredential).where(GoogleCredential.company_id == DEMO_COMPANY_ID)
    cred = (await db.execute(cred_query)).scalar_one_or_none()

    docs_count = 0
    pending_count = 0
    try:
        from app.db.models import KnowledgeDocument
        docs_count = (
            await db.execute(
                select(KnowledgeDocument).where(KnowledgeDocument.company_id == DEMO_COMPANY_ID)
            )
        ).scalars().all()
        docs_count = len(docs_count)
    except Exception:
        docs_count = 0

    try:
        pending_count = (
            await db.execute(
                select(EmailLog).where(
                    EmailLog.company_id == DEMO_COMPANY_ID,
                    EmailLog.status == "PENDING_APPROVAL",
                )
            )
        ).scalars().all()
        pending_count = len(pending_count)
    except Exception:
        pending_count = 0

    return templates.TemplateResponse(
        "settings.html",
        {
            "request": request,
            "google_connected": bool(cred and cred.is_active),
            "google_email": cred.email_address if cred else None,
            "docs_count": docs_count,
            "pending_count": pending_count,
            "settings": settings,
        },
    )


@router.get("/settings/disconnect", response_class=RedirectResponse)
async def settings_disconnect(db: AsyncSession = Depends(get_db)):
    cred_query = select(GoogleCredential).where(GoogleCredential.company_id == DEMO_COMPANY_ID)
    cred = (await db.execute(cred_query)).scalar_one_or_none()
    if cred:
        cred.is_active = False
        await db.commit()
    return RedirectResponse(url="/settings", status_code=status.HTTP_303_SEE_OTHER)
