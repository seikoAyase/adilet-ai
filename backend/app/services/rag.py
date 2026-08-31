import logging
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.schemas.chat import ChatResponse, Citation
from backend.app.services.retrieval import search_legal_chunks
from backend.app.services.llm import (
    extract_citations,
    get_agentic_llm_service,
)

logger = logging.getLogger("kz_legal_rag.rag")


async def answer_legal_question(
    session: AsyncSession,
    question: str,
    top_k: int = 5,
    code_name: Optional[str] = None,
    temperature: float = 0.0,
) -> ChatResponse:
    # If user explicitly specified a code_name filter
    if code_name and code_name.strip() and code_name.strip().lower() not in ("string", "null", "none"):
        sources = await search_legal_chunks(session=session, query=question, top_k=top_k, code_name=code_name)
        if not sources:
            return ChatResponse(
                question=question,
                answer="В указанном кодексе не найдено релевантных статей по данному вопросу.",
                citations=[],
                sources=[],
            )
        from backend.app.services.llm import KZ_LEGAL_SYSTEM_PROMPT
        from backend.app.services.llm import get_agentic_llm_service

        agent = get_agentic_llm_service()
        raw_answer, _ = await agent.chat_with_tools(session=session, question=question, temperature=temperature)
        citations = extract_citations(raw_answer, sources)
        if not citations and sources:
            top_src = sources[0]
            citations.append(
                Citation(
                    source_index=1,
                    document_title=top_src.document_title,
                    code_name=top_src.code_name,
                    article_number=top_src.article_number,
                    article_title=top_src.article_title,
                    clause_number=top_src.clause_number,
                    source_url=top_src.source_url,
                )
            )
        return ChatResponse(question=question, answer=raw_answer, citations=citations, sources=sources)

    # Autonomous Tool Calling: Gemini decides which code and query to search
    agent = get_agentic_llm_service()
    raw_answer, sources = await agent.chat_with_tools(session=session, question=question, temperature=temperature)

    citations = extract_citations(raw_answer, sources)

    if not citations and sources:
        top_src = sources[0]
        citations.append(
            Citation(
                source_index=1,
                document_title=top_src.document_title,
                code_name=top_src.code_name,
                article_number=top_src.article_number,
                article_title=top_src.article_title,
                clause_number=top_src.clause_number,
                source_url=top_src.source_url,
            )
        )

    return ChatResponse(
        question=question,
        answer=raw_answer,
        citations=citations,
        sources=sources,
    )
