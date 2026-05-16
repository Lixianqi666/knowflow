import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, Float, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID

from app.database import Base


class EmployeeProfile(Base):
    __tablename__ = "employee_profiles"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(80), nullable=False, index=True)
    employee_no = Column(String(50), nullable=False, unique=True)
    department = Column(String(100), nullable=False)
    level = Column(String(30), nullable=False)
    manager_name = Column(String(80), nullable=False)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)


class TravelReceipt(Base):
    __tablename__ = "travel_receipts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    employee_name = Column(String(80), nullable=False, index=True)
    receipt_type = Column(String(30), nullable=False)
    amount = Column(Float, nullable=False)
    city = Column(String(80), nullable=False)
    occurred_at = Column(DateTime(timezone=True), nullable=False)
    is_valid = Column(String(10), nullable=False, default="true")
    extra = Column("metadata", JSONB, default=dict)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)


class ReimbursementRequest(Base):
    __tablename__ = "reimbursement_requests"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    employee_name = Column(String(80), nullable=False, index=True)
    trip_city = Column(String(80), nullable=True)
    amount = Column(Float, nullable=False, default=0)
    status = Column(String(30), nullable=False, default="submitted")
    detail = Column(Text, default="")
    receipt_ids = Column(JSONB, default=list)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
