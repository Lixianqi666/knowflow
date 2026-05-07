from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_current_user
from app.database import get_db
from app.models.feedback import Feedback
from app.models.user import User
from app.services.webhook import dispatch as webhook_dispatch

router = APIRouter(prefix="/feedback", tags=["反馈"])


class FeedbackCreate(BaseModel):
    query: str
    conversation_id: str | None = None
    feedback_type: str  # transfer_human / record_issue
    message: str | None = None


@router.post("/")
async def create_feedback(
    data: FeedbackCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    feedback = Feedback(
        user_id=user.id,
        conversation_id=data.conversation_id,
        query=data.query,
        feedback_type=data.feedback_type,
        message=data.message,
    )
    db.add(feedback)
    await db.flush()
    await webhook_dispatch(
        db,
        "feedback.created",
        {
            "feedback_id": str(feedback.id),
            "query": data.query,
            "feedback_type": data.feedback_type,
            "user_id": str(user.id),
        },
    )
    return {"detail": "反馈已记录", "id": str(feedback.id)}
