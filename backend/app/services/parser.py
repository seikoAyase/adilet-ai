import re
from typing import List, Optional
from bs4 import BeautifulSoup
from pydantic import BaseModel


class ParsedChunk(BaseModel):
    section: Optional[str] = None
    chapter: Optional[str] = None
    article_number: str
    article_title: str
    clause_number: Optional[str] = None
    context_header: str
    content: str
    chunk_index: int = 0


RE_SECTION = re.compile(r"^РАЗДЕЛ\s+([0-9IVXLCDM]+)[\.\s]*(.*)", re.IGNORECASE)
RE_CHAPTER = re.compile(r"^Глава\s+(\d+)[\.\s]*(.*)", re.IGNORECASE)
RE_ARTICLE = re.compile(r"^Статья\s+(\d+(?:-\d+)?)[\.\s]*(.*)", re.IGNORECASE)


def clean_text(text: str) -> str:
    if not text:
        return ""
    text = text.replace("\xa0", " ").replace("&nbsp;", " ")
    return " ".join(text.split()).strip()


def parse_adilet_html(html_content: str, doc_title: str = "Трудовой кодекс РК") -> List[ParsedChunk]:
    soup = BeautifulSoup(html_content, "html.parser")

    for tag in soup(["script", "style", "head", "nav", "div.container_aside", "div.container_bside"]):
        tag.decompose()

    current_section: Optional[str] = None
    current_chapter: Optional[str] = None
    current_art_num: Optional[str] = None
    current_art_title: Optional[str] = None
    current_art_paragraphs: List[str] = []

    chunks: List[ParsedChunk] = []
    chunk_counter = 1

    def flush_current_article():
        nonlocal chunk_counter
        if current_art_num is not None and current_art_paragraphs:
            article_body = "\n\n".join(current_art_paragraphs).strip()
            if article_body:
                context_parts = [f"[{doc_title}"]
                if current_section:
                    context_parts.append(current_section)
                if current_chapter:
                    context_parts.append(current_chapter)
                context_parts.append(f"Статья {current_art_num}. {current_art_title or ''}".strip())
                context_header = " -> ".join(context_parts) + "]"

                chunk = ParsedChunk(
                    section=current_section,
                    chapter=current_chapter,
                    article_number=current_art_num,
                    article_title=current_art_title or "",
                    clause_number=None,
                    context_header=context_header,
                    content=article_body,
                    chunk_index=chunk_counter,
                )
                chunks.append(chunk)
                chunk_counter += 1

    for element in soup.find_all(["p", "div"]):
        if "note" in element.get("class", []):
            continue

        raw_p_text = element.get_text(separator=" ", strip=True)
        text = clean_text(raw_p_text)
        if not text:
            continue

        match_section = RE_SECTION.match(text)
        if match_section:
            flush_current_article()
            current_art_num = None
            current_art_title = None
            current_art_paragraphs = []
            current_section = text
            continue

        match_chapter = RE_CHAPTER.match(text)
        if match_chapter:
            flush_current_article()
            current_art_num = None
            current_art_title = None
            current_art_paragraphs = []
            current_chapter = text
            continue

        match_article = RE_ARTICLE.match(text)
        if match_article:
            flush_current_article()
            current_art_num = match_article.group(1).strip()
            current_art_title = clean_text(match_article.group(2).strip())
            current_art_paragraphs = []
            continue

        if current_art_num is not None:
            if text.startswith("Сноска.") or text.startswith("Примечание ИЗПИ!"):
                continue
            current_art_paragraphs.append(text)

    flush_current_article()
    return chunks