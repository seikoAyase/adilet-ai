from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.database import get_db
from backend.app.schemas.chat import ChatRequest, ChatResponse
from backend.app.services.rag import answer_legal_question

router = APIRouter()


@router.post(
    "/chat",
    response_model=ChatResponse,
    summary="Legal RAG Chat",
    status_code=status.HTTP_200_OK,
)
async def chat_rag_endpoint(
    req: ChatRequest,
    db: AsyncSession = Depends(get_db),
):
    return await answer_legal_question(
        session=db,
        question=req.question,
        top_k=req.top_k,
        code_name=req.code_name,
        temperature=req.temperature,
    )
