import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID

from app.database import Base


class AgentRun(Base):
    __tablename__ = "agent_runs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(UUID(as_uuid=True), ForeignKey("agent_sessions.id", ondelete="CASCADE"), nullable=True, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    goal = Column(Text, nullable=False)
    status = Column(String(30), nullable=False, default="running")
    final_answer = Column(Text, nullable=True)
    failure_reason = Column(Text, nullable=True)
    total_steps = Column(Integer, default=0)
    total_tokens = Column(Integer, default=0)
    total_latency_ms = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)


class AgentStepTrace(Base):
    __tablename__ = "agent_step_traces"
    __table_args__ = (Index("idx_agent_step_run_step", "run_id", "step_index"),)

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    run_id = Column(UUID(as_uuid=True), ForeignKey("agent_runs.id", ondelete="CASCADE"), nullable=False, index=True)
    step_index = Column(Integer, nullable=False)
    phase = Column(String(30), nullable=False)
    thought = Column(Text, default="")
    action = Column(JSONB, default=dict)
    observation = Column(JSONB, default=dict)
    latency_ms = Column(Integer, default=0)
    tokens = Column(Integer, default=0)
    error = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
