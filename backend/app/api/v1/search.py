from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.database import get_db
from backend.app.schemas.search import SearchRequest, SearchResponse
from backend.app.services.retrieval import search_legal_chunks

router = APIRouter()


@router.post(
    "/search",
    response_model=SearchResponse,
    summary="Semantic Search",
    status_code=status.HTTP_200_OK,
)
async def search_law_endpoint(
    req: SearchRequest,
    db: AsyncSession = Depends(get_db),
):
    results = await search_legal_chunks(
        session=db,
        query=req.query,
        top_k=req.top_k,
        code_name=req.code_name,
        min_score=req.min_score,
    )
    return SearchResponse(
        query=req.query,
        total_found=len(results),
        results=results,
    )
