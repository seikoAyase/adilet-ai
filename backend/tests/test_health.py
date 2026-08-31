import asyncio
import pytest
from httpx import ASGITransport, AsyncClient

from backend.main import app


@pytest.mark.asyncio
async def test_health_check():
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        response = await client.get("/api/v1/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["database"] == "connected"
        assert "active" in data["pgvector"]


if __name__ == "__main__":
    async def main():
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            resp = await client.get("/api/v1/health")
            print("STATUS CODE:", resp.status_code)
            print("BODY:", resp.json())
            root_resp = await client.get("/")
            print("ROOT BODY:", root_resp.json())

    asyncio.run(main())
