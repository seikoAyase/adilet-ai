import os
import re
import json
import logging
from abc import ABC, abstractmethod
from typing import Any, Callable, Dict, List, Optional, Tuple
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.schemas.search import SearchResultItem
from backend.app.schemas.chat import Citation
from backend.app.services.retrieval import search_legal_chunks

logger = logging.getLogger("kz_legal_rag.llm")

KZ_LEGAL_SYSTEM_PROMPT = """Ты — высококвалифицированный юридический AI-ассистент по законодательству Республики Казахстан.

У тебя есть инструмент `search_legislation` для поиска официальных статей законов и кодексов РК.

ПРАВИЛА:
1. ВСЕГДА используй инструмент `search_legislation`, чтобы найти точные статьи закона перед тем, как отвечать на юридический вопрос.
2. Подбирай точный параметр `code_name`:
   - 'koap_rk': КоАП РК (штрафы, нарушения ПДД, административная ответственность)
   - 'tk_rk': Трудовой кодекс РК (трудовые договоры, увольнения, отпуска, зарплата)
   - 'uk_rk': Уголовный кодекс РК (преступления, уголовная ответственность, наказания)
   - 'appk_rk': АППК РК (жалобы на госорганы, административные процедуры)
   - 'consumer_rights': Закон о защите прав потребителей (возврат товара, гарантии)
   - 'too_law': Закон о ТОО (уставной капитал, доли, учреждение компаний)
   - null или 'all': если вопрос затрагивает несколько законов или ты не уверен в кодексе.
3. Отвечай СТРОГО на основании найденных источников, указывая ссылки в формате [1], [2].
4. Запрещено придумывать статьи или использовать законы других стран.
"""

LEGAL_SEARCH_TOOL_DECLARATION = {
    "name": "search_legislation",
    "description": "Поиск официальных статей и правовых норм законодательства Республики Казахстан в базе данных.",
    "parameters": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Оптимизированный юридический поисковый запрос (например: 'превышение скорости штраф' или 'срок уведомления об увольнении')."
            },
            "code_name": {
                "type": "string",
                "description": "Код конкретного закона: 'koap_rk', 'tk_rk', 'uk_rk', 'appk_rk', 'consumer_rights', 'too_law' или null для поиска по всем законам.",
                "enum": ["koap_rk", "tk_rk", "uk_rk", "appk_rk", "consumer_rights", "too_law", "all"]
            },
            "top_k": {
                "type": "integer",
                "description": "Количество статей для выборки (по умолчанию 4).",
                "default": 4
            }
        },
        "required": ["query"]
    }
}


def extract_citations(answer: str, sources: List[SearchResultItem]) -> List[Citation]:
    matches = re.findall(r"\[(\d+)\]", answer)
    cited_indices = sorted(list(set(int(m) for m in matches)))

    citations: List[Citation] = []
    for idx in cited_indices:
        if 1 <= idx <= len(sources):
            src = sources[idx - 1]
            citations.append(
                Citation(
                    source_index=idx,
                    document_title=src.document_title,
                    code_name=src.code_name,
                    article_number=src.article_number,
                    article_title=src.article_title,
                    clause_number=src.clause_number,
                    source_url=src.source_url,
                )
            )
    return citations


class BaseAgenticLLM(ABC):
    @abstractmethod
    async def chat_with_tools(
        self,
        session: AsyncSession,
        question: str,
        temperature: float = 0.0,
    ) -> Tuple[str, List[SearchResultItem]]:
        pass


class GeminiAgenticService(BaseAgenticLLM):
    def __init__(self, api_key: str, model_name: str = "gemini-2.5-flash"):
        self.api_key = api_key
        self.model_name = model_name

    async def chat_with_tools(
        self,
        session: AsyncSession,
        question: str,
        temperature: float = 0.0,
    ) -> Tuple[str, List[SearchResultItem]]:
        all_sources: List[SearchResultItem] = []

        try:
            from google import genai
            from google.genai import types

            client = genai.Client(api_key=self.api_key)

            # Tool definition for google-genai
            search_func = types.FunctionDeclaration(
                name="search_legislation",
                description="Поиск по официальным нормам и статьям законодательства Казахстана.",
                parameters=types.Schema(
                    type=types.Type.OBJECT,
                    properties={
                        "query": types.Schema(type=types.Type.STRING, description="Оптимизированный поисковый запрос"),
                        "code_name": types.Schema(
                            type=types.Type.STRING,
                            description="Код закона: 'koap_rk', 'tk_rk', 'uk_rk', 'appk_rk', 'consumer_rights', 'too_law' или null для всех",
                        ),
                        "top_k": types.Schema(type=types.Type.INTEGER, description="Число статей (по умолчанию 4)"),
                    },
                    required=["query"],
                ),
            )
            tool = types.Tool(function_declarations=[search_func])

            chat = client.aio.chats.create(
                model=self.model_name,
                config=types.GenerateContentConfig(
                    system_instruction=KZ_LEGAL_SYSTEM_PROMPT,
                    temperature=temperature,
                    tools=[tool],
                ),
            )

            # Step 1: Send user question to Gemini
            response = await chat.send_message(question)

            # Step 2: Check if Gemini decided to call search tool
            if response.function_calls:
                for call in response.function_calls:
                    if call.name == "search_legislation":
                        args = call.args or {}
                        query = args.get("query", question)
                        code = args.get("code_name")
                        if code == "all" or code == "null":
                            code = None
                        top_k = int(args.get("top_k", 4))

                        logger.info("Gemini autonomously calling tool search_legislation(query='%s', code_name='%s')", query, code)
                        sources = await search_legal_chunks(session=session, query=query, top_k=top_k, code_name=code)
                        all_sources.extend(sources)

                        # Format source context for Gemini tool response
                        tool_context = []
                        for idx, src in enumerate(sources, start=1):
                            tool_context.append(
                                f"--- ИСТОЧНИК [{idx}] ---\n"
                                f"Документ: {src.document_title} ({src.code_name})\n"
                                f"Статья: № {src.article_number} «{src.article_title}»\n"
                                f"Текст нормы:\n{src.content}\n"
                            )
                        formatted_tool_output = "\n".join(tool_context) if tool_context else "Статьи не найдены."

                        # Step 3: Return tool results back to Gemini
                        followup = await chat.send_message(
                            types.Part.from_function_response(
                                name="search_legislation",
                                response={"result": formatted_tool_output},
                            )
                        )
                        return followup.text or "", all_sources

            return response.text or "", all_sources

        except Exception as exc:
            logger.warning("Gemini tool call fallback: %s. Performing direct retrieval.", exc)
            # Fallback to direct semantic retrieval
            sources = await search_legal_chunks(session=session, query=question, top_k=4)
            if not sources:
                return "В базе данных законодательства РК не найдено релевантных статей.", []

            context = "\n".join([f"[{i+1}] {s.document_title} ст.{s.article_number}: {s.content}" for i, s in enumerate(sources)])
            return f"Согласно законодательству РК [1]:\n{sources[0].content}", sources


class FallbackAgenticService(BaseAgenticLLM):
    async def chat_with_tools(
        self,
        session: AsyncSession,
        question: str,
        temperature: float = 0.0,
    ) -> Tuple[str, List[SearchResultItem]]:
        sources = await search_legal_chunks(session=session, query=question, top_k=4)
        if not sources:
            return "В базе данных законодательства РК не найдено релевантных статей по вашему запросу.", []

        top_src = sources[0]
        answer = (
            f"На основании норм законодательства Республики Казахстан ({top_src.document_title}, Статья {top_src.article_number}) [1]:\n\n"
            f"{top_src.content}"
        )
        return answer, sources


def get_agentic_llm_service() -> BaseAgenticLLM:
    from backend.app.core.config import settings
    gemini_key = settings.GEMINI_API_KEY or os.getenv("GEMINI_API_KEY")
    if gemini_key:
        return GeminiAgenticService(api_key=gemini_key, model_name=settings.GEMINI_MODEL)
    return FallbackAgenticService()
