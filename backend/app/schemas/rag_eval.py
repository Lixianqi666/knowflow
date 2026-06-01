from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class RagEvalCaseCreate(BaseModel):
    knowledge_base_id: str | None = None
    question: str
    expected_answer: str | None = None
    expected_citation_doc_ids: list[str] = []
    tags: list[str] = []


class RagEvalCaseUpdate(BaseModel):
    question: str | None = None
    expected_answer: str | None = None
    expected_citation_doc_ids: list[str] | None = None
    tags: list[str] | None = None


class RagEvalCaseOut(BaseModel):
    id: UUID
    knowledge_base_id: UUID | None = None
    question: str
    expected_answer: str | None = None
    expected_citation_doc_ids: list = []
    tags: list = []
    created_by: UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class RagEvalRunOut(BaseModel):
    id: UUID
    case_id: UUID
    question: str
    answer: str | None = None
    citations: list = []
    passed: bool
    score: float | None = None
    failure_reason: str | None = None
    created_by: UUID
    created_at: datetime

    class Config:
        from_attributes = True
