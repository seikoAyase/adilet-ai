import asyncio
from sqlalchemy import select, func
from backend.app.core.database import async_session_maker
from backend.app.models.document import Document
from backend.app.models.chunk import DocumentChunk
from backend.app.services.rag import answer_legal_question


async def main():
    async with async_session_maker() as session:
        docs = (await session.execute(select(Document))).scalars().all()
        total_chunks = (await session.execute(select(func.count(DocumentChunk.id)))).scalar()
        print(f"\n================ DATABASE STATUS ================")
        print(f"Total Laws/Codes Ingested: {len(docs)}")
        print(f"Total Legal Articles/Chunks: {total_chunks}")
        for d in docs:
            print(f" * [{d.code_name}] {d.title}")
        print(f"=================================================\n")

        # Test RAG across different branches of law
        test_questions = [
            "Какой штраф за превышение скорости от 20 до 40 км/ч в Казахстане?",
            "В какой срок потребитель может вернуть товар надлежащего качества?",
            "Какой минимальный размер уставного капитала для субъекта малого предпринимательства в ТОО?",
        ]

        for q in test_questions:
            resp = await answer_legal_question(session=session, question=q, top_k=2)
            print(f"Q: {resp.question}")
            print(f"Found source: {resp.sources[0].context_header if resp.sources else 'None'}")
            print(f"Score: {resp.sources[0].similarity_score if resp.sources else 'None'}")
            print("-" * 50)


if __name__ == "__main__":
    asyncio.run(main())
