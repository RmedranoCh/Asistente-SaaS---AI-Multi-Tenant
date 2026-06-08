from fastapi import APIRouter

from app.views.web_auth import router as auth_router
from app.views.web_dashboard import router as dashboard_router
from app.views.web_settings import router as settings_router

views_router = APIRouter()
views_router.include_router(auth_router)
views_router.include_router(dashboard_router)
views_router.include_router(settings_router)
