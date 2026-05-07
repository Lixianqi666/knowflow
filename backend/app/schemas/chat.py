from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class ConversationCreate(BaseModel):
    title: str | None = None


class ConversationUpdate(BaseModel):
    title: str


class ConversationOut(BaseModel):
    id: UUID
    title: str | None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class MessageCreate(BaseModel):
    content: str
    template_id: str | None = None


class MessageOut(BaseModel):
    id: UUID
    role: str
    content: str
    sources: list = []
    rating: int | None = None
    created_at: datetime

    class Config:
        from_attributes = True


class SSEEvent(BaseModel):
    type: str  # sources / token / done / error
    data: str | list | dict


class MessageRatingCreate(BaseModel):
    rating: int  # 1=赞, -1=踩
