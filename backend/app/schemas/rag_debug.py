from pydantic import BaseModel, Field


class RagDebugSearchRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=500)
    knowledge_base_id: str | None = None
    top_k: int = Field(default=5, ge=1, le=20)


class RagDebugSearchResult(BaseModel):
    rank: int
    document_id: str
    document_title: str
    chunk_id: str
    snippet: str
    score: float
    page: int | None = None
    locator: dict | None = None


class RagDebugSearchResponse(BaseModel):
    query: str
    knowledge_base_id: str | None = None
    top_k: int
    results: list[RagDebugSearchResult]
    no_result_reason: str | None = None
