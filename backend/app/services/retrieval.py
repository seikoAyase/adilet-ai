import logging
from typing import List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.document import Document
from backend.app.models.chunk import DocumentChunk
from backend.app.schemas.search import SearchResultItem
from backend.app.services.embeddings import get_embedding_service

logger = logging.getLogger("kz_legal_rag.retrieval")


async def search_legal_chunks(
    session: AsyncSession,
    query: str,
    top_k: int = 5,
    code_name: Optional[str] = None,
    min_score: float = 0.0,
) -> List[SearchResultItem]:
    embed_service = get_embedding_service()
    query_vector = embed_service.embed_query(query)

    cosine_dist = DocumentChunk.embedding.cosine_distance(query_vector).label("distance")

    stmt = (
        select(DocumentChunk, Document, cosine_dist)
        .join(Document, DocumentChunk.document_id == Document.id)
        .where(Document.is_active == True)
        .where(DocumentChunk.embedding.is_not(None))
    )

    if code_name and code_name.strip() and code_name.strip().lower() not in ("string", "null", "none"):
        stmt = stmt.where(Document.code_name == code_name.strip())

    stmt = stmt.order_by(cosine_dist.asc()).limit(top_k)

    result = await session.execute(stmt)
    rows = result.all()

    search_results: List[SearchResultItem] = []
    for chunk, doc, dist in rows:
        similarity = max(0.0, min(1.0, 1.0 - float(dist)))
        if similarity < min_score:
            continue

        item = SearchResultItem(
            chunk_id=chunk.id,
            document_id=doc.id,
            document_title=doc.title,
            code_name=doc.code_name,
            section=chunk.section,
            chapter=chunk.chapter,
            article_number=chunk.article_number,
            article_title=chunk.article_title,
            clause_number=chunk.clause_number,
            context_header=chunk.context_header,
            content=chunk.content,
            source_url=doc.source_url,
            similarity_score=round(similarity, 4),
        )
        search_results.append(item)

    return search_results
