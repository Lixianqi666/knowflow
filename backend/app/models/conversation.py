import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship

from app.database import Base


class Conversation(Base):
    __tablename__ = "conversations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True)
    title = Column(String(255))
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        index=True,
    )

    messages = relationship("Message", cascade="all, delete-orphan", passive_deletes=True)


class Message(Base):
    __tablename__ = "messages"
    __table_args__ = (Index("idx_messages_conversation", "conversation_id", "created_at"),)

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    conversation_id = Column(UUID(as_uuid=True), ForeignKey("conversations.id", ondelete="CASCADE"))
    role = Column(String(20), nullable=False, index=True)  # user / assistant / system
    content = Column(Text, nullable=False)
    sources = Column(JSONB, default=list)
    token_count = Column(Integer)
    rating = Column(Integer, nullable=True, index=True)  # 1=赞, -1=踩
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
