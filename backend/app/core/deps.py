from fastapi import Depends, HTTPException

from app.core.security import get_current_user
from app.models.user import User


async def get_current_admin(user: User = Depends(get_current_user)) -> User:
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="需要管理员权限")
    return user
