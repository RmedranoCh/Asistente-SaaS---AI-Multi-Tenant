

UPLOAD_URL = "/api/v1/settings/knowledge/upload"


class TestKnowledgeUploadValidation:
    async def test_rejects_unsupported_extension(self, client):
        resp = await client.post(
            UPLOAD_URL,
            files={"file": ("doc.exe", b"MZ...", "application/octet-stream")},
        )
        assert resp.status_code == 400

    async def test_rejects_oversized_file(self, client):
        big_content = b"x" * (10 * 1024 * 1024 + 1)
        resp = await client.post(
            UPLOAD_URL,
            files={"file": ("big.txt", big_content, "text/plain")},
        )
        assert resp.status_code == 413

    async def test_rejects_empty_text_file(self, client):
        resp = await client.post(
            UPLOAD_URL,
            files={"file": ("vacio.txt", b"", "text/plain")},
        )
        assert resp.status_code == 400


class TestKnowledgeUploadSuccess:
    async def test_uploads_txt_and_indexes(self, client, monkeypatch, session_factory):
        ingested = {}

        class FakeRagEngine:
            def ingest_tenant_document(self, company_id, text_content, filename):
                ingested.update(
                    {
                        "company_id": company_id,
                        "text_content": text_content,
                        "filename": filename,
                    }
                )

        import app.core.rag.engine as rag_engine_module

        monkeypatch.setattr(rag_engine_module, "rag_engine", FakeRagEngine())

        content = "Política de reembolsos: dentro de los primeros 30 días."
        resp = await client.post(
            UPLOAD_URL,
            files={"file": ("licencia.md", content.encode("utf-8"), "text/markdown")},
        )
        assert resp.status_code == 200
        assert "licencia.md" in resp.text

        from app.db.models import KnowledgeDocument

        async with session_factory() as db:
            from sqlalchemy import select

            docs = (await db.execute(select(KnowledgeDocument))).scalars().all()
        assert len(docs) == 1
        assert docs[0].filename == "licencia.md"
        assert docs[0].chunk_count >= 1
        assert ingested["text_content"] == content