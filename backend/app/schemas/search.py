from typing import List, Optional
from pydantic import BaseModel, Field


class SearchRequest(BaseModel):
    """
    Search request query parameters.
    """
    query: str = Field(
        ...,
        min_length=2,
        max_length=1000,
        description="User search query or question",
        examples=["В какой срок работник должен предупредить об увольнении по собственному желанию?"],
    )
    top_k: int = Field(default=5, ge=1, le=50, description="Number of relevant article chunks to return")
    code_name: Optional[str] = Field(default=None, description="Optional filter by legal code (e.g. 'tk_rk' or null for all)")
    min_score: float = Field(default=0.0, ge=0.0, le=1.0, description="Minimum cosine similarity threshold (0.0 to 1.0)")


class SearchResultItem(BaseModel):
    """
    Detailed information about a matched legal chunk.
    """
    chunk_id: int
    document_id: int
    document_title: str
    code_name: str
    section: Optional[str] = None
    chapter: Optional[str] = None
    article_number: str
    article_title: str
    clause_number: Optional[str] = None
    context_header: str
    content: str
    source_url: Optional[str] = None
    similarity_score: float = Field(..., description="Cosine similarity score (0.0 to 1.0)")


class SearchResponse(BaseModel):
    """
    Response schema for vector search endpoint.
    """
    query: str
    total_found: int
    results: List[SearchResultItem]
