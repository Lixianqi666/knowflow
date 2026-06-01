import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship

from app.database import Base

# 知识库 RAG 默认配置
DEFAULT_RAG_CONFIG = {
    "top_k": 5,
    "score_threshold": 0.0,
    "chunk_size": 1000,
    "chunk_overlap": 150,
    "no_evidence_policy": "strict",
}


class KnowledgeBase(Base):
    __tablename__ = "knowledge_bases"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(100), nullable=False)
    description = Column(Text, default="")
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    rag_config = Column(JSONB, nullable=True, default=None)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    agents = relationship(
        "Agent", secondary="agent_knowledge_bases", back_populates="knowledge_bases"
    )
