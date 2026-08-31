from fastapi import APIRouter
from backend.app.api.v1.health import router as health_router
from backend.app.api.v1.search import router as search_router
from backend.app.api.v1.chat import router as chat_router
from backend.app.api.v1.ingest import router as ingest_router

api_router = APIRouter()

api_router.include_router(health_router, tags=["Health"])
api_router.include_router(search_router, tags=["Search"])
api_router.include_router(chat_router, tags=["Chat"])
api_router.include_router(ingest_router, tags=["Ingest"])
