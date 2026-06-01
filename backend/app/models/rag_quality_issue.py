import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID

from app.database import Base


class RagQualityIssue(Base):
    __tablename__ = "rag_quality_issues"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    knowledge_base_id = Column(
        UUID(as_uuid=True),
        ForeignKey("knowledge_bases.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    source_type = Column(String(20), nullable=False, index=True)  # feedback / eval_failed / no_evidence / manual
    source_id = Column(String(255), nullable=True)  # message_id 或 run_id
    question = Column(Text, nullable=True)
    answer = Column(Text, nullable=True)
    citations = Column(JSONB, default=list)
    severity = Column(String(10), nullable=False, default="medium")  # low / medium / high
    status = Column(String(20), nullable=False, default="open", index=True)  # open / in_progress / resolved / ignored
    reason = Column(Text, nullable=True)
    resolution_note = Column(Text, nullable=True)
    assignee_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
    resolved_at = Column(DateTime(timezone=True), nullable=True)
