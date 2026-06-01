from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class RagQualityIssueCreate(BaseModel):
    knowledge_base_id: str | None = None
    question: str | None = None
    answer: str | None = None
    citations: list = []
    severity: str = "medium"
    reason: str | None = None
    source_type: str = "manual"
    source_id: str | None = None


class RagQualityIssueUpdate(BaseModel):
    status: str | None = None
    severity: str | None = None
    resolution_note: str | None = None
    assignee_user_id: str | None = None


class RagQualityIssueOut(BaseModel):
    id: UUID
    knowledge_base_id: UUID | None = None
    source_type: str
    source_id: str | None = None
    question: str | None = None
    answer: str | None = None
    citations: list = []
    severity: str
    status: str
    reason: str | None = None
    resolution_note: str | None = None
    assignee_user_id: UUID | None = None
    created_by: UUID | None = None
    created_at: datetime
    updated_at: datetime
    resolved_at: datetime | None = None

    class Config:
        from_attributes = True
