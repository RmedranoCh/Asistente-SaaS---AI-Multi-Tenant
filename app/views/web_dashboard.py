import uuid
from fastapi import APIRouter, Request, Depends, HTTPException, status
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.config import settings
from app.db.session import get_db
from app.db.models import EmailLog

router = APIRouter(tags=["UI Dashboard"])
templates = Jinja2Templates(directory="app/templates")

DEMO_COMPANY_ID = uuid.UUID("99999999-9999-9999-9999-999999999999")


@router.get("/dashboard", response_class=HTMLResponse)
async def dashboard_page(request: Request, db: AsyncSession = Depends(get_db)):
    return templates.TemplateResponse(
        "dashboard.html",
        {"request": request, "company_id": str(DEMO_COMPANY_ID), "settings": settings},
    )


@router.get("/dashboard/stats", response_class=HTMLResponse)
async def dashboard_stats_partial(request: Request, db: AsyncSession = Depends(get_db)):
    query = (
        select(EmailLog.status, func.count(EmailLog.id))
        .where(EmailLog.company_id == DEMO_COMPANY_ID)
        .group_by(EmailLog.status)
    )
    result = await db.execute(query)
    stats = {row[0]: row[1] for row in result.all()}

    pending = stats.get("PENDING_APPROVAL", 0)
    sent = stats.get("AUTO_SENT", 0) + stats.get("MANUALLY_APPROVED", 0)
    total = sum(stats.values())

    return templates.TemplateResponse(
        "components/stats_cards.html",
        {
            "request": request,
            "pending_count": pending,
            "sent_count": sent,
            "total_count": total,
        },
    )


@router.get("/dashboard/emails", response_class=HTMLResponse)
async def dashboard_emails_partial(request: Request, db: AsyncSession = Depends(get_db)):
    query = (
        select(EmailLog)
        .where(EmailLog.company_id == DEMO_COMPANY_ID)
        .order_by(EmailLog.received_at.desc())
        .limit(15)
    )
    result = await db.execute(query)
    emails = result.scalars().all()

    return templates.TemplateResponse(
        "components/email_row.html",
        {"request": request, "emails": emails},
    )


@router.post("/dashboard/emails/{email_id}/approve", response_class=HTMLResponse)
async def approve_email_action(
    email_id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    query = select(EmailLog).where(
        EmailLog.id == email_id, EmailLog.company_id == DEMO_COMPANY_ID
    )
    result = await db.execute(query)
    email_log = result.scalar_one_or_none()

    if not email_log:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Correo no encontrado.",
        )

    if email_log.status == "MANUALLY_APPROVED":
        return HTMLResponse(
            content=(
                "<div id='alert-container' hx-swap-oob='true'>"
                "<div class='bg-blue-100 text-blue-800 p-2 rounded'>Este correo ya fue enviado.</div>"
                "</div>"
            )
        )

    form = {}
    try:
        form = dict(await request.form())
    except Exception:
        form = {}

    final_reply = (form.get("final_reply") or "").strip()
    if final_reply:
        email_log.approved_reply = final_reply
        email_log.suggested_reply = final_reply
    else:
        final_reply = email_log.suggested_reply or ""

    if not final_reply.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="La respuesta final no puede estar vacía.",
        )

    from app.workers.tasks import send_approved_email

    email_log.status = "APPROVING"
    await db.commit()

    send_approved_email.delay(str(email_log.id), final_reply)

    return HTMLResponse(
        content=(
            "<div id='alert-container' hx-swap-oob='true'>"
            "<div class='bg-green-100 text-green-800 p-2 rounded'>"
            "Correo aprobado y encolado para envío."
            "</div></div>"
        )
    )


@router.post("/dashboard/emails/{email_id}/reject", response_class=HTMLResponse)
async def reject_email_action(
    email_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    query = select(EmailLog).where(
        EmailLog.id == email_id, EmailLog.company_id == DEMO_COMPANY_ID
    )
    result = await db.execute(query)
    email_log = result.scalar_one_or_none()

    if not email_log:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Correo no encontrado.",
        )

    email_log.status = "REJECTED"
    await db.commit()

    return HTMLResponse(
        content=(
            "<div id='alert-container' hx-swap-oob='true'>"
            "<div class='bg-yellow-100 text-yellow-800 p-2 rounded'>"
            "El correo fue descartado."
            "</div></div>"
        )
    )
