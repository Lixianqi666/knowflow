from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime


@dataclass
class RawDocument:
    external_id: str
    title: str
    content: str
    metadata: dict
    permissions: list[str] = None  # 有权限的用户ID列表


class BaseConnector(ABC):
    @abstractmethod
    async def fetch_documents(self, since: datetime | None = None) -> list[RawDocument]: ...

    @abstractmethod
    async def fetch_document(self, doc_id: str) -> RawDocument: ...
