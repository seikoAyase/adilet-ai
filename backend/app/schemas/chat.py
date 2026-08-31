from typing import List, Optional
from pydantic import BaseModel, Field
from backend.app.schemas.search import SearchResultItem


class Citation(BaseModel):
    """
    Formal legal citation referencing a specific article of Kazakhstan legislation.
    """
    source_index: int = Field(..., description="Numeric citation index matching prompt [1], [2], etc.")
    document_title: str
    code_name: str
    article_number: str
    article_title: str
    clause_number: Optional[str] = None
    source_url: Optional[str] = None


class ChatRequest(BaseModel):
    """
    Request payload for Legal RAG QA / Chat.
    """
    question: str = Field(
        ...,
        min_length=2,
        max_length=1500,
        description="Question about Kazakhstan law",
        examples=["Какой испытательный срок может быть установлен работнику в Казахстане?"],
    )
    top_k: int = Field(default=5, ge=1, le=20, description="Number of legal sources to provide to LLM")
    code_name: Optional[str] = Field(default=None, description="Optional restriction to a specific code (e.g. 'tk_rk' or null for all)")
    temperature: float = Field(default=0.0, ge=0.0, le=1.0, description="Sampling temperature (0.0 for strict factuality)")


class ChatResponse(BaseModel):
    """
    Full Legal RAG response including the grounded answer, extracted citations, and source chunks.
    """
    question: str
    answer: str
    citations: List[Citation] = Field(default_factory=list, description="Verified legal references cited in the answer")
    sources: List[SearchResultItem] = Field(default_factory=list, description="Raw legal chunks passed as context to the LLM")
