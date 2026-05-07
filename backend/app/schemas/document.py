from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class DataSourceCreate(BaseModel):
    name: str
    type: str  # notion / feishu / confluence / local
    config: dict = {}


class DataSourceOut(BaseModel):
    id: UUID
    name: str
    type: str
    status: str
    last_sync_at: datetime | None
    created_at: datetime

    class Config:
        from_attributes = True


class DocumentOut(BaseModel):
    id: UUID
    title: str
    status: str
    indexed_at: datetime | None
    created_at: datetime

    class Config:
        from_attributes = True
