from fastapi import APIRouter
from app.api.v1 import google_oauth, webhooks, knowledge, mock_test

api_router = APIRouter()

api_router.include_router(google_oauth.router, prefix="/oauth", tags=["Google OAuth2"])
api_router.include_router(webhooks.router, prefix="/webhooks", tags=["Webhooks Ingesta"])
api_router.include_router(knowledge.router, prefix="", tags=["Knowledge RAG"])
api_router.include_router(mock_test.router, prefix="", tags=["Mock Testing"])
