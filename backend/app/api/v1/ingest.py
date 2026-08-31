from pathlib import Path
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from backend.app.services.loader import ingest_html_file

router = APIRouter()


class IngestRequest(BaseModel):
    file_path: str = Field(..., description="Path to HTML law file")
    title: str = Field(default="Трудовой кодекс Республики Казахстан")
    code_name: str = Field(default="tk_rk")
    act_type: str = Field(default="КОДЕКС")
    source_url: str = Field(default="https://adilet.zan.kz/rus/docs/K1500000414")


@router.post(
    "/ingest",
    summary="Ingest Legal Document",
    status_code=status.HTTP_200_OK,
)
async def ingest_document_endpoint(req: IngestRequest):
    target = Path(req.file_path)
    if not target.is_absolute():
        from backend.app.core.config import BASE_DIR
        target = BASE_DIR / req.file_path

    if not target.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"File not found: {target}",
        )

    total_chunks = await ingest_html_file(
        file_path=target,
        title=req.title,
        code_name=req.code_name,
        act_type=req.act_type,
        source_url=req.source_url,
    )

    return {
        "status": "success",
        "document": req.title,
        "code_name": req.code_name,
        "chunks_indexed": total_chunks,
    }
