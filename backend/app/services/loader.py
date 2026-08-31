import asyncio
import logging
from pathlib import Path
from typing import List, Optional
from sqlalchemy import select, delete, text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.database import async_session_maker, engine
from backend.app.models import Base
from backend.app.models.document import Document
from backend.app.models.chunk import DocumentChunk
from backend.app.services.parser import parse_adilet_html, ParsedChunk
from backend.app.services.embeddings import get_embedding_service

logger = logging.getLogger("kz_legal_rag.loader")


async def load_document_to_db(
    session: AsyncSession,
    title: str,
    code_name: str,
    chunks: List[ParsedChunk],
    act_type: str = "КОДЕКС",
    source_url: Optional[str] = None,
    language: str = "ru",
    with_embeddings: bool = True,
) -> Document:
    async with engine.begin() as conn:
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        await conn.run_sync(Base.metadata.create_all)

    stmt = select(Document).where(Document.code_name == code_name)
    result = await session.execute(stmt)
    document = result.scalar_one_or_none()

    if document is None:
        document = Document(
            title=title,
            code_name=code_name,
            act_type=act_type,
            source_url=source_url,
            is_active=True,
            language=language,
        )
        session.add(document)
        await session.flush()
    else:
        document.title = title
        document.act_type = act_type
        document.source_url = source_url
        document.is_active = True
        document.language = language
        
        await session.execute(
            delete(DocumentChunk).where(DocumentChunk.document_id == document.id)
        )
        await session.flush()

    embeddings = [None] * len(chunks)
    if with_embeddings and chunks:
        embed_service = get_embedding_service()
        texts_to_embed = [f"{c.context_header}\n\n{c.content}" for c in chunks]
        embeddings = embed_service.embed_documents(texts_to_embed)

    db_chunks = [
        DocumentChunk(
            document_id=document.id,
            section=chunk.section,
            chapter=chunk.chapter,
            article_number=chunk.article_number,
            article_title=chunk.article_title,
            clause_number=chunk.clause_number,
            context_header=chunk.context_header,
            content=chunk.content,
            chunk_index=chunk.chunk_index,
            embedding=embeddings[idx],
        )
        for idx, chunk in enumerate(chunks)
    ]

    session.add_all(db_chunks)
    await session.commit()
    return document


async def ingest_html_file(
    file_path: Path,
    title: str = "Трудовой кодекс Республики Казахстан",
    code_name: str = "tk_rk",
    act_type: str = "КОДЕКС",
    source_url: str = "https://adilet.zan.kz/rus/docs/K1500000414",
    language: str = "ru",
) -> int:
    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
        html_content = f.read()

    chunks = parse_adilet_html(html_content, doc_title=title)

    async with async_session_maker() as session:
        await load_document_to_db(
            session=session,
            title=title,
            code_name=code_name,
            chunks=chunks,
            act_type=act_type,
            source_url=source_url,
            language=language,
        )
        return len(chunks)


if __name__ == "__main__":
    import sys

    logging.basicConfig(level=logging.INFO)
    default_path = Path(__file__).resolve().parent.parent.parent / "data" / "raw" / "Трудовой кодекс Республики Казахстан.html"
    target_path = Path(sys.argv[1]) if len(sys.argv) > 1 else default_path
    
    total = asyncio.run(ingest_html_file(target_path))
    print(f"Ingested {total} articles into database.")
