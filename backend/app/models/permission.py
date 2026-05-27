import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID

from app.database import Base


class DocumentPermission(Base):
    __tablename__ = "document_permissions"
    __table_args__ = (UniqueConstraint("document_id", "user_id", name="uq_doc_user"),)

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id = Column(UUID(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE"))
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"))
    permission = Column(String(20), nullable=False, default="read")
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


class SourcePermission(Base):
    __tablename__ = "source_permissions"
    __table_args__ = (UniqueConstraint("source_id", "user_id", name="uq_source_user"),)

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source_id = Column(UUID(as_uuid=True), ForeignKey("data_sources.id", ondelete="CASCADE"))
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"))
    permission = Column(String(20), nullable=False, default="read")
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
