from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class ConversationCreate(BaseModel):
    title: str | None = None
    goal: str | None = None


class ConversationUpdate(BaseModel):
    title: str | None = None
    goal: str | None = None


class ConversationOut(BaseModel):
    id: UUID
    title: str | None
    is_pinned: bool = False
    pinned_at: datetime | None = None
    goal: str | None = None
    goal_summary: str | None = None
    goal_status: str = "active"
    missing_info: list = []
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class MessageCreate(BaseModel):
    content: str
    template_id: str | None = None
    goal: str | None = None
    knowledge_base_id: str | None = None


class MessageOut(BaseModel):
    id: UUID
    role: str
    content: str
    sources: list = []
    citations: list = []
    rating: int | None = None
    created_at: datetime

    class Config:
        from_attributes = True


class SSEEvent(BaseModel):
    type: str  # sources / token / done / error
    data: str | list | dict


class MessageRatingCreate(BaseModel):
    rating: int  # 1=赞, -1=踩


class MessageFeedbackCreate(BaseModel):
    rating: str  # "up" / "down"
    reason: str | None = None


class MessageFeedbackOut(BaseModel):
    id: UUID
    message_id: UUID
    user_id: UUID
    rating: str
    reason: str | None = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
