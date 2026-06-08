import os
import uuid
from io import BytesIO

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from fastapi.responses import HTMLResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.session import get_db
from app.db.models import KnowledgeDocument, GoogleCredential

router = APIRouter(tags=["UI Settings API"])

DEMO_COMPANY_ID = uuid.UUID("99999999-9999-9999-9999-999999999999")

ALLOWED_EXTENSIONS = {".txt", ".md", ".markdown", ".pdf"}
MAX_FILE_BYTES = 10 * 1024 * 1024


def _read_pdf(content_bytes: bytes) -> str:
    try:
        from pypdf import PdfReader
    except ImportError:
        return ""
    reader = PdfReader(BytesIO(content_bytes))
    chunks = []
    for page in reader.pages:
        try:
            chunks.append(page.extract_text() or "")
        except Exception:
            continue
    return "\n".join(chunks).strip()


@router.post("/settings/knowledge/upload", response_class=HTMLResponse)
async def upload_knowledge(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    filename = file.filename or "documento.txt"
    ext = os.path.splitext(filename)[1].lower()

    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Extensión {ext} no soportada. Use una de: {sorted(ALLOWED_EXTENSIONS)}",
        )

    content_bytes = await file.read()
    if len(content_bytes) > MAX_FILE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"El archivo excede el límite de {MAX_FILE_BYTES // (1024*1024)}MB.",
        )

    if ext == ".pdf":
        text_content = _read_pdf(content_bytes)
        if not text_content:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No se pudo extraer texto del PDF (¿está escaneado o protegido?).",
            )
    else:
        try:
            text_content = content_bytes.decode("utf-8")
        except UnicodeDecodeError:
            text_content = content_bytes.decode("latin-1", errors="replace")

    if not text_content.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El archivo está vacío.",
        )

    try:
        from app.core.rag.engine import rag_engine

        rag_engine.ingest_tenant_document(
            company_id=str(DEMO_COMPANY_ID),
            text_content=text_content,
            filename=filename,
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al vectorizar el documento: {str(e)}",
        )

    chunk_estimate = max(1, len(text_content) // 800)
    doc = KnowledgeDocument(
        company_id=DEMO_COMPANY_ID,
        filename=filename,
        chunk_count=chunk_estimate,
    )
    db.add(doc)
    await db.commit()

    return HTMLResponse(
        content=(
            "<div id='alert-container' hx-swap-oob='true'>"
            f"<div class='bg-green-100 text-green-800 p-2 rounded'>"
            f"Documento '{filename}' indexado ({chunk_estimate} chunks aprox)."
            "</div></div>"
        )
    )
