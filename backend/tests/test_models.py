import pytest
from sqlalchemy import select
from backend.app.core.database import async_session_maker
from backend.app.models.document import Document
from backend.app.models.chunk import DocumentChunk
from backend.app.core.config import settings


@pytest.mark.asyncio
async def test_create_and_query_vector_chunk():
    async with async_session_maker() as session:
        # Create parent document (e.g. Labor Code RK)
        doc = Document(
            title="Трудовой кодекс Республики Казахстан",
            code_name="tk_rk_test",
            act_type="КОДЕКС",
            source_url="https://adilet.zan.kz/rus/docs/K1500000414",
            is_active=True,
            language="ru",
        )
        session.add(doc)
        await session.flush()  # populate doc.id

        # Dummy embedding vector of dimension settings.EMBEDDING_DIMENSION (1536)
        dummy_vector = [0.01] * settings.EMBEDDING_DIMENSION
        dummy_vector[0] = 0.99

        # Create child chunk with hierarchical context
        chunk = DocumentChunk(
            document_id=doc.id,
            section="Раздел 2. Трудовые отношения",
            chapter="Глава 4. Трудовой договор",
            article_number="56",
            article_title="Порядок расторжения трудового договора по инициативе работника",
            clause_number="1",
            context_header="[ТК РК -> Раздел 2 -> Глава 4 -> Статья 56. Расторжение по инициативе работника]",
            content="Работник вправе по своей инициативе расторгнуть трудовой договор, уведомив об этом работодателя письменно не менее чем за один месяц...",
            chunk_index=1,
            embedding=dummy_vector,
        )
        session.add(chunk)
        await session.commit()

        # Query chunk by cosine distance using pgvector
        query_vector = [0.01] * settings.EMBEDDING_DIMENSION
        query_vector[0] = 0.95

        stmt = (
            select(DocumentChunk)
            .where(DocumentChunk.document_id == doc.id)
            .order_by(DocumentChunk.embedding.cosine_distance(query_vector))
            .limit(1)
        )
        result = await session.execute(stmt)
        matched_chunk = result.scalar_one_or_none()

        assert matched_chunk is not None
        assert matched_chunk.article_number == "56"
        assert matched_chunk.article_title == "Порядок расторжения трудового договора по инициативе работника"
        assert matched_chunk.document.code_name == "tk_rk_test"

        # Cleanup test document and cascade-deleted chunks
        await session.delete(doc)
        await session.commit()
