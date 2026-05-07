"""RabbitMQ 消息协议定义"""

import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from uuid import uuid4


@dataclass
class IndexTaskMessage:
    task_id: str
    idempotency_key: str
    task_type: str = "index_document"
    payload: dict = None
    retry_count: int = 0
    max_retries: int = 2
    created_at: str = ""

    def __post_init__(self):
        if not self.task_id:
            self.task_id = str(uuid4())
        if not self.created_at:
            self.created_at = datetime.now(timezone.utc).isoformat()
        if self.payload is None:
            self.payload = {}

    def to_json(self) -> str:
        return json.dumps(asdict(self), ensure_ascii=False)

    @classmethod
    def from_json(cls, data: str) -> "IndexTaskMessage":
        d = json.loads(data)
        return cls(**d)

    @classmethod
    def create(cls, document_id: str, content_hash: str) -> "IndexTaskMessage":
        return cls(
            task_id=str(uuid4()),
            idempotency_key=f"doc:{document_id}:{content_hash}",
            payload={"document_id": document_id},
        )
