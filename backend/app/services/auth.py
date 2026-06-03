import logging
import re

from fastapi import HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import (
    create_access_token,
    create_refresh_token,
    hash_password,
    set_refresh_cookie,
    verify_password,
)
from app.models.user import User
from app.schemas.user import Token, UserCreate, UserLogin, UserOut

logger = logging.getLogger(__name__)

# 登录失败锁定阈值：连续失败 5 次后锁定 15 分钟
_MAX_FAILED_LOGINS = 5
_LOCKOUT_SECONDS = 900


def _validate_password(password: str) -> None:
    """校验密码策略"""
    if len(password) < 8:
        raise HTTPException(status_code=400, detail="密码至少 8 位且包含字母和数字")
    if len(password) > 128:
        raise HTTPException(status_code=400, detail="密码不能超过 128 位")
    if not password.strip():
        raise HTTPException(status_code=400, detail="密码不能全为空白字符")
    has_letter = bool(re.search(r'[a-zA-Z]', password))
    has_digit = bool(re.search(r'[0-9]', password))
    if not (has_letter and has_digit):
        raise HTTPException(status_code=400, detail="密码至少 8 位且包含字母和数字")


class AuthService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def register(self, data: UserCreate, response: Response) -> Token:
        _validate_password(data.password)

        result = await self.db.execute(select(User).where(User.email == data.email))
        if result.scalar_one_or_none():
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="注册信息无效，请检查后重试")

        user = User(
            email=data.email,
            name=data.name,
            hashed_password=hash_password(data.password),
        )
        self.db.add(user)
        await self.db.flush()

        access_token, _ = create_access_token(str(user.id))
        refresh_token, _, max_age = create_refresh_token(str(user.id))
        set_refresh_cookie(response, refresh_token, max_age)
        logger.info(f"用户注册成功 (id={user.id})")
        return Token(access_token=access_token, user=UserOut.model_validate(user))

    async def login(self, data: UserLogin, response: Response, request=None) -> Token:
        result = await self.db.execute(select(User).where(User.email == data.email))
        user = result.scalar_one_or_none()

        # 用户不存在或密码错误
        if not user or not verify_password(data.password, user.hashed_password):
            # 如果用户存在，递增失败计数
            if user:
                user.failed_login_count = (user.failed_login_count or 0) + 1

            from app.services.audit import record_audit_event

            await record_audit_event(
                self.db,
                action="auth.login.failed",
                status="failed",
                request=request,
                metadata={"reason": "invalid_credentials"},
            )
            await self.db.commit()
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="账号或密码错误")

        # 账号锁定检查
        if (user.failed_login_count or 0) >= _MAX_FAILED_LOGINS:
            from app.services.audit import record_audit_event

            await record_audit_event(
                self.db,
                action="auth.login.locked",
                status="failed",
                request=request,
                metadata={"reason": "account_locked"},
            )
            raise HTTPException(
                status_code=status.HTTP_423_LOCKED,
                detail=f"账号已锁定，请 {_LOCKOUT_SECONDS // 60} 分钟后重试",
            )

        # 账号被禁用
        if not user.is_active:
            user.failed_login_count = (user.failed_login_count or 0) + 1

            from app.services.audit import record_audit_event

            await record_audit_event(
                self.db,
                action="auth.login.failed",
                status="failed",
                request=request,
                metadata={"reason": "disabled"},
            )
            await self.db.commit()
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="账号或密码错误")

        # 登录成功：清零失败计数
        user.failed_login_count = 0
        access_token, _ = create_access_token(str(user.id))
        refresh_token, _, max_age = create_refresh_token(str(user.id))
        set_refresh_cookie(response, refresh_token, max_age)

        from app.services.audit import record_audit_event

        await record_audit_event(
            self.db,
            actor_user=user,
            action="auth.login.success",
            request=request,
        )
        logger.info(f"用户登录成功 (id={user.id})")
        return Token(access_token=access_token, user=UserOut.model_validate(user))
