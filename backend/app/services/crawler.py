import asyncio
import logging
from pathlib import Path
from typing import Dict, List
import httpx

from backend.app.core.config import BASE_DIR
from backend.app.services.loader import ingest_html_file

logging.basicConfig(level=logging.INFO, format="%(asctime)s - [%(levelname)s] - %(message)s")
logger = logging.getLogger("kz_legal_rag.crawler")

# Catalog of foundational Codes and Laws of the Republic of Kazakhstan from adilet.zan.kz
KZ_LEGAL_CATALOG: List[Dict[str, str]] = [
    {
        "code_name": "koap_rk",
        "title": "Кодекс Республики Казахстан об административных правонарушениях (КоАП РК)",
        "act_type": "КОДЕКС",
        "doc_id": "K1400000235",
        "url": "https://adilet.zan.kz/rus/docs/K1400000235",
    },
    {
        "code_name": "uk_rk",
        "title": "Уголовный кодекс Республики Казахстан (УК РК)",
        "act_type": "КОДЕКС",
        "doc_id": "K1400000226",
        "url": "https://adilet.zan.kz/rus/docs/K1400000226",
    },
    {
        "code_name": "gk_rk_gen",
        "title": "Гражданский кодекс Республики Казахстан (Общая часть)",
        "act_type": "КОДЕКС",
        "doc_id": "K940001000_",
        "url": "https://adilet.zan.kz/rus/docs/K940001000_",
    },
    {
        "code_name": "gk_rk_spec",
        "title": "Гражданский кодекс Республики Казахстан (Особенная часть)",
        "act_type": "КОДЕКС",
        "doc_id": "K990000409_",
        "url": "https://adilet.zan.kz/rus/docs/K990000409_",
    },
    {
        "code_name": "appk_rk",
        "title": "Административный процедурно-процессуальный кодекс Республики Казахстан (АППК РК)",
        "act_type": "КОДЕКС",
        "doc_id": "K2000000350",
        "url": "https://adilet.zan.kz/rus/docs/K2000000350",
    },
    {
        "code_name": "consumer_rights",
        "title": "Закон Республики Казахстан «О защите прав потребителей»",
        "act_type": "ЗАКОН",
        "doc_id": "Z100000274_",
        "url": "https://adilet.zan.kz/rus/docs/Z100000274_",
    },
    {
        "code_name": "too_law",
        "title": "Закон Республики Казахстан «О товариществах с ограниченной и дополнительной ответственностью» (ТОО)",
        "act_type": "ЗАКОН",
        "doc_id": "Z980000220_",
        "url": "https://adilet.zan.kz/rus/docs/Z980000220_",
    },
]


async def download_law_html(url: str, output_path: Path) -> bool:
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    try:
        async with httpx.AsyncClient(timeout=60.0, follow_redirects=True, verify=False) as client:
            logger.info("Downloading %s ...", url)
            response = await client.get(url, headers=headers)
            if response.status_code == 200 and len(response.text) > 5000:
                output_path.parent.mkdir(parents=True, exist_ok=True)
                with open(output_path, "w", encoding="utf-8") as f:
                    f.write(response.text)
                logger.info("Saved %s (%d bytes)", output_path.name, len(response.text))
                return True
            else:
                logger.warning("Failed to download %s: HTTP %d (length %d)", url, response.status_code, len(response.text))
                return False
    except Exception as exc:
        logger.error("Error downloading %s: %s", url, exc)
        return False


async def ingest_all_kz_laws():
    raw_dir = BASE_DIR / "backend" / "data" / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)

    logger.info("Starting automated crawling & ingestion of Kazakhstan legislation...")

    for law in KZ_LEGAL_CATALOG:
        code_name = law["code_name"]
        title = law["title"]
        file_path = raw_dir / f"{code_name}.html"

        if not file_path.exists():
            success = await download_law_html(law["url"], file_path)
            if not success:
                continue

        try:
            total_chunks = await ingest_html_file(
                file_path=file_path,
                title=title,
                code_name=code_name,
                act_type=law["act_type"],
                source_url=law["url"],
            )
            logger.info("Successfully ingested '%s': %d articles indexed.", code_name, total_chunks)
        except Exception as exc:
            logger.error("Failed to ingest '%s': %s", code_name, exc)

    logger.info("KZ Legislation crawler and ingestion completed.")


if __name__ == "__main__":
    asyncio.run(ingest_all_kz_laws())
