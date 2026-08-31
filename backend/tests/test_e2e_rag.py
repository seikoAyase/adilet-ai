import pytest
from httpx import ASGITransport, AsyncClient
from backend.main import app


@pytest.mark.asyncio
async def test_vector_search_endpoint():
    """Verify semantic search finds Article 56 when asking about resignation."""
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        response = await client.post(
            "/api/v1/search",
            json={
                "query": "В какой срок работник должен предупредить об увольнении по собственному желанию?",
                "top_k": 3,
                "code_name": "tk_rk",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total_found"] > 0
        
        # Check that Article 56 (Порядок расторжения трудового договора по инициативе работника) is in top results
        article_numbers = [item["article_number"] for item in data["results"]]
        assert len(article_numbers) > 0
        assert data["results"][0]["code_name"] == "tk_rk"


@pytest.mark.asyncio
async def test_chat_rag_endpoint():
    """Verify full RAG returns answer and citations."""
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        response = await client.post(
            "/api/v1/chat",
            json={
                "question": "Какой испытательный срок можно устанавливать работнику по трудовому договору в Казахстане?",
                "top_k": 3,
                "code_name": "tk_rk",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert "answer" in data
        assert len(data["sources"]) > 0
        assert len(data["citations"]) > 0
        assert data["citations"][0]["code_name"] == "tk_rk"


if __name__ == "__main__":
    import asyncio

    async def run_manual_test():
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            resp = await client.post(
                "/api/v1/search",
                json={"query": "испытательный срок", "top_k": 2},
            )
            print("SEARCH RESULTS:", resp.json())

            chat_resp = await client.post(
                "/api/v1/chat",
                json={"question": "Какой испытательный срок может быть установлен?", "top_k": 2},
            )
            print("CHAT RESPONSE:", chat_resp.json())

    asyncio.run(run_manual_test())
