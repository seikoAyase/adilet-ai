import pytest
from sqlalchemy import text
from backend.app.core.database import engine, Base
import backend.app.models  # load models


@pytest.fixture(autouse=True)
async def prepare_and_cleanup_database():
    """Ensure vector extension & tables exist, and dispose engine per test loop."""
    async with engine.begin() as conn:
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        await conn.run_sync(Base.metadata.create_all)
    yield
    await engine.dispose()
