from typing import Any

from app.config import settings
from app.core.rag.embeddings import embedding_provider


class MultiTenantRAGEngine:
    """Motor RAG multi-inquilino con pgvector.

    Toda la infraestructura pesada (llama_index, el vector store de
    PostgreSQL y el modelo de embeddings) se inicializa de forma diferida
    para evitar conexiones y descargas innecesarias al importar el módulo.
    """

    def __init__(self) -> None:
        self._embed_model: Any | None = None
        self._vector_store: Any | None = None
        self._storage_context: Any | None = None

    @property
    def embed_model(self) -> Any:
        if self._embed_model is None:
            self._embed_model = embedding_provider.get_embedding_model()
        return self._embed_model

    @property
    def vector_store(self) -> Any:
        if self._vector_store is None:
            from llama_index.vector_stores.postgres import PGVectorStore

            sync_db_url = str(settings.DATABASE_URL)
            async_db_url = str(settings.DATABASE_URL).replace(
                "postgresql://", "postgresql+asyncpg://"
            )
            self._vector_store = PGVectorStore.from_params(
                connection_string=sync_db_url,
                async_connection_string=async_db_url,
                table_name="tenant_knowledge_vectors",
                embed_dim=384,
            )
        return self._vector_store

    @property
    def storage_context(self) -> Any:
        if self._storage_context is None:
            from llama_index.core import StorageContext

            self._storage_context = StorageContext.from_defaults(
                vector_store=self.vector_store
            )
        return self._storage_context

    def ingest_tenant_document(self, company_id: str, text_content: str, filename: str) -> None:
        from llama_index.core import Document, VectorStoreIndex

        document = Document(
            text=text_content,
            metadata={
                "company_id": str(company_id),
                "source_file": filename,
            },
        )

        VectorStoreIndex.from_documents(
            [document],
            storage_context=self.storage_context,
            embed_model=self.embed_model,
            show_progress=False,
        )

    def query_tenant_knowledge(self, company_id: str, query_text: str, similarity_top_k: int = 3) -> str:
        from llama_index.core import VectorStoreIndex
        from llama_index.core.vector_stores import MetadataFilter, MetadataFilters

        index = VectorStoreIndex.from_vector_store(
            vector_store=self.vector_store,
            embed_model=self.embed_model,
        )

        filters = MetadataFilters(
            filters=[
                MetadataFilter(key="company_id", value=str(company_id), operator="==")
            ]
        )

        query_engine = index.as_query_engine(
            similarity_top_k=similarity_top_k,
            filters=filters,
        )

        response = query_engine.query(query_text)
        return str(response)


rag_engine = MultiTenantRAGEngine()