from fastapi import APIRouter, Depends, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.config import settings
from backend.app.core.database import get_db

router = APIRouter()


@router.get(
    "/health",
    summary="Health Check",
    status_code=status.HTTP_200_OK,
)
async def health_check(db: AsyncSession = Depends(get_db)):
    health_status = {
        "service": settings.PROJECT_NAME,
        "status": "healthy",
        "database": "unknown",
        "pgvector": "unknown",
    }

    try:
        result = await db.execute(text("SELECT 1"))
        if result.scalar() == 1:
            health_status["database"] = "connected"

        vec_result = await db.execute(
            text("SELECT extversion FROM pg_extension WHERE extname = 'vector'")
        )
        vec_version = vec_result.scalar()
        if vec_version:
            health_status["pgvector"] = f"active (v{vec_version})"
        else:
            health_status["pgvector"] = "not_active"
            health_status["status"] = "degraded"

    except Exception as exc:
        health_status["status"] = "unhealthy"
        health_status["database"] = f"error: {str(exc)}"

    return health_status
