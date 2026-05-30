import uuid
from datetime import datetime, timedelta, timezone

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.models.user import User

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security_scheme = HTTPBearer(auto_error=False)

BLACKLIST_PREFIX_ACCESS = "auth:blacklist:access:"
BLACKLIST_PREFIX_REFRESH = "auth:blacklist:refresh:"


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def create_access_token(user_id: str) -> tuple[str, str]:
    """返回 (token, jti)"""
    jti = uuid.uuid4().hex
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    token = jwt.encode(
        {"sub": user_id, "exp": expire, "type": "access", "jti": jti},
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM,
    )
    return token, jti


def create_refresh_token(user_id: str) -> tuple[str, str, int]:
    """返回 (token, jti, max_age_seconds)"""
    jti = uuid.uuid4().hex
    expire = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    token = jwt.encode(
        {"sub": user_id, "exp": expire, "type": "refresh", "jti": jti},
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM,
    )
    max_age = settings.REFRESH_TOKEN_EXPIRE_DAYS * 86400
    return token, jti, max_age


def decode_token(token: str, expected_type: str = "access") -> dict:
    """解码并校验 token，返回 payload。保证 sub/jti/type 存在。"""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    except (JWTError, KeyError):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="无效的认证凭据")
    if payload.get("type") != expected_type:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="无效的认证凭据")
    if not payload.get("sub"):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="无效的认证凭据")
    if not payload.get("jti"):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="无效的认证凭据")
    return payload


async def _check_blacklist(jti: str, prefix: str) -> None:
    """检查 jti 是否在黑名单中"""
    from app.core.ratelimit import get_redis

    try:
        r = await get_redis()
        if await r.exists(f"{prefix}{jti}"):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="无效的认证凭据")
    except HTTPException:
        raise
    except Exception:
        # Redis 不可用时安全优先，拒绝请求
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="认证服务暂不可用")


async def blacklist_token(jti: str, prefix: str, ttl: int, user_id: str = "") -> None:
    """将 jti 加入黑名单，写入失败时抛出 503"""
    from app.core.ratelimit import get_redis

    try:
        r = await get_redis()
        await r.set(f"{prefix}{jti}", user_id, ex=ttl)
    except Exception:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="认证服务暂不可用")


async def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(security_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    if not credentials:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="未提供认证凭据")
    payload = decode_token(credentials.credentials, expected_type="access")
    user_id = payload["sub"]
    jti = payload.get("jti", "")
    await _check_blacklist(jti, BLACKLIST_PREFIX_ACCESS)
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="用户不存在或已禁用")
    return user


def set_refresh_cookie(response, token: str, max_age: int) -> None:
    """设置 refresh token HttpOnly cookie"""
    response.set_cookie(
        key="refresh_token",
        value=token,
        httponly=True,
        samesite="lax",
        secure=settings.ENVIRONMENT == "production",
        max_age=max_age,
        path="/api/v1/auth",
    )


def clear_refresh_cookie(response) -> None:
    """清除 refresh token cookie"""
    response.delete_cookie(key="refresh_token", path="/api/v1/auth")
