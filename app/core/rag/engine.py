import os
from typing import List
from llama_index.core import VectorStoreIndex, StorageContext, Document
from llama_index.vector_stores.postgres import PGVectorStore
from llama_index.core.vector_stores import MetadataFilter, MetadataFilters

from app.config import settings
from app.core.rag.embeddings import embedding_provider

class MultiTenantRAGEngine:
    def __init__(self):
        self.embed_model = embedding_provider.get_embedding_model()
        
        sync_db_url = str(settings.DATABASE_URL)
        async_db_url = str(settings.DATABASE_URL).replace("postgresql://", "postgresql+asyncpg://")
        
        self.vector_store = PGVectorStore.from_params(
            connection_string=sync_db_url,
            async_connection_string=async_db_url,
            table_name="tenant_knowledge_vectors",
            embed_dim=384
        )
        
        self.storage_context = StorageContext.from_defaults(vector_store=self.vector_store)

    def ingest_tenant_document(self, company_id: str, text_content: str, filename: str) -> None:
        document = Document(
            text=text_content,
            metadata={
                "company_id": str(company_id),
                "source_file": filename
            }
        )
        
        VectorStoreIndex.from_documents(
            [document],
            storage_context=self.storage_context,
            embed_model=self.embed_model,
            show_progress=False
        )

    def query_tenant_knowledge(self, company_id: str, query_text: str, similarity_top_k: int = 3) -> str:
        index = VectorStoreIndex.from_vector_store(
            vector_store=self.vector_store,
            embed_model=self.embed_model
        )
        
        filters = MetadataFilters(
            filters=[
                MetadataFilter(key="company_id", value=str(company_id), operator="==")
            ]
        )
        
        query_engine = index.as_query_engine(
            similarity_top_k=similarity_top_k,
            filters=filters
        )
        
        response = query_engine.query(query_text)
        return str(response)

rag_engine = MultiTenantRAGEngine()