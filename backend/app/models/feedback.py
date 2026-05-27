import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID

from app.database import Base


class Feedback(Base):
    __tablename__ = "feedbacks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    conversation_id = Column(
        UUID(as_uuid=True), ForeignKey("conversations.id", ondelete="SET NULL"), nullable=True
    )
    query = Column(Text, nullable=False)
    feedback_type = Column(String(20), nullable=False)  # transfer_human / record_issue
    message = Column(Text, nullable=True)
    status = Column(String(20), default="pending")  # pending / processing / resolved
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
