import uuid
import logging
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete

from app.config import settings
from app.db.session import get_db
from app.db.models import (
    Company,
    GoogleCredential,
    MockInboxEmail,
    MockSentEmail,
    MockCalendarEvent,
    MockCrmActivity,
)
from app.db.security import encryptor

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/mock", tags=["Mock Testing"])

DEMO_COMPANY_ID = uuid.UUID("99999999-9999-9999-9999-999999999999")
DEMO_EMAIL = "demo@example.com"


@router.post("/seed")
async def seed_mock_data(db: AsyncSession = Depends(get_db)):
    company = await db.get(Company, DEMO_COMPANY_ID)
    if not company:
        company = Company(id=DEMO_COMPANY_ID, name="Demo Company (Mock)")
        db.add(company)

    cred = await db.execute(
        select(GoogleCredential).where(GoogleCredential.company_id == DEMO_COMPANY_ID)
    )
    if not cred.scalar_one_or_none():
        dummy_token = encryptor.encrypt_token("mock_refresh_token")
        google_cred = GoogleCredential(
            company_id=DEMO_COMPANY_ID,
            email_address=DEMO_EMAIL,
            encrypted_refresh_token=dummy_token,
            is_active=True,
        )
        db.add(google_cred)

    existing = await db.execute(
        select(MockInboxEmail).where(MockInboxEmail.company_id == DEMO_COMPANY_ID)
    )
    if existing.scalars().first():
        return {
            "status": "ok",
            "message": "Los datos mock ya existen. Usa POST /mock/reset para reiniciar.",
        }

    emails = [
        MockInboxEmail(
            company_id=DEMO_COMPANY_ID,
            gmail_message_id="mock_msg_001",
            gmail_thread_id="mock_thread_001",
            sender="cliente@external.com",
            subject="Consulta sobre horarios de atención",
            body_content="Hola, quería saber cuáles son los horarios de atención al cliente durante el fin de semana. Gracias.",
            history_id="100",
        ),
        MockInboxEmail(
            company_id=DEMO_COMPANY_ID,
            gmail_message_id="mock_msg_002",
            gmail_thread_id="mock_thread_002",
            sender="juan@example.com",
            subject="Solicitud de reembolso",
            body_content="Compré un producto la semana pasada pero no funciona correctamente. Solicito la devolución de mi dinero. Número de pedido: #12345.",
            history_id="101",
        ),
        MockInboxEmail(
            company_id=DEMO_COMPANY_ID,
            gmail_message_id="mock_msg_003",
            gmail_thread_id="mock_thread_003",
            sender="reunion@cliente.com",
            subject="Agendar reunión para demo del producto",
            body_content="Hola, me gustaría agendar una reunión para ver una demo del producto. Estoy disponible el jueves a las 3pm.",
            history_id="102",
        ),
        MockInboxEmail(
            company_id=DEMO_COMPANY_ID,
            gmail_message_id="mock_msg_004",
            gmail_thread_id="mock_thread_004",
            sender="quejoso@example.com",
            subject="Queja - Mal servicio técnico",
            body_content="Hace una semana reporté un problema y aún no recibo respuesta. Es inaceptable la demora. Quiero hablar con un supervisor.",
            history_id="103",
        ),
    ]
    for e in emails:
        db.add(e)
    await db.commit()

    return {
        "status": "ok",
        "message": f"Se sembraron {len(emails)} correos mock para company_id={DEMO_COMPANY_ID}",
        "company_id": str(DEMO_COMPANY_ID),
        "mock_emails": [
            {
                "gmail_message_id": e.gmail_message_id,
                "sender": e.sender,
                "subject": e.subject,
                "history_id": e.history_id,
            }
            for e in emails
        ],
    }


@router.post("/reset")
async def reset_mock_data(db: AsyncSession = Depends(get_db)):
    for table in [MockInboxEmail, MockSentEmail, MockCalendarEvent, MockCrmActivity]:
        await db.execute(delete(table))
    await db.commit()
    return {"status": "ok", "message": "Datos mock eliminados."}


@router.get("/inbox")
async def list_mock_inbox(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(MockInboxEmail).order_by(MockInboxEmail.created_at.desc())
    )
    emails = result.scalars().all()
    return {
        "count": len(emails),
        "emails": [
            {
                "id": str(e.id),
                "gmail_message_id": e.gmail_message_id,
                "sender": e.sender,
                "subject": e.subject,
                "body": e.body_content[:200],
                "history_id": e.history_id,
                "is_processed": e.is_processed,
                "created_at": e.created_at.isoformat(),
            }
            for e in emails
        ],
    }


@router.get("/sent")
async def list_mock_sent(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(MockSentEmail).order_by(MockSentEmail.sent_at.desc())
    )
    sent = result.scalars().all()
    return {
        "count": len(sent),
        "sent": [
            {
                "id": str(s.id),
                "to_email": s.to_email,
                "subject": s.subject,
                "body": s.body_text[:200],
                "status": s.status,
                "sent_at": s.sent_at.isoformat(),
            }
            for s in sent
        ],
    }


@router.get("/events")
async def list_mock_events(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(MockCalendarEvent).order_by(MockCalendarEvent.created_at.desc())
    )
    events = result.scalars().all()
    return {
        "count": len(events),
        "events": [
            {
                "id": str(e.id),
                "summary": e.summary,
                "start_iso": e.start_iso,
                "end_iso": e.end_iso,
                "attendee_email": e.attendee_email,
                "event_id": e.event_id,
            }
            for e in events
        ],
    }


@router.get("/crm")
async def list_mock_crm(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(MockCrmActivity).order_by(MockCrmActivity.created_at.desc())
    )
    activities = result.scalars().all()
    return {
        "count": len(activities),
        "activities": [
            {
                "id": str(a.id),
                "email": a.email,
                "activity_type": a.activity_type,
                "notes": a.notes,
                "status": a.status,
                "created_at": a.created_at.isoformat(),
            }
            for a in activities
        ],
    }
