from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.ratelimit import auth_rate_limit
from app.core.security import (
    BLACKLIST_PREFIX_ACCESS,
    BLACKLIST_PREFIX_REFRESH,
    blacklist_token,
    clear_refresh_cookie,
    create_access_token,
    create_refresh_token,
    decode_token,
    set_refresh_cookie,
)
from app.database import get_db
from app.models.user import User
from app.schemas.user import Token, UserCreate, UserLogin, UserOut
from app.services.auth import AuthService

router = APIRouter(prefix="/auth", tags=["认证"])


@router.post("/register", response_model=Token)
async def register(
    data: UserCreate,
    response: Response,
    _: None = Depends(auth_rate_limit),
    db: AsyncSession = Depends(get_db),
):
    return await AuthService(db).register(data, response)


@router.post("/login", response_model=Token)
async def login(
    data: UserLogin,
    request: Request,
    response: Response,
    _: None = Depends(auth_rate_limit),
    db: AsyncSession = Depends(get_db),
):
    return await AuthService(db).login(data, response, request=request)


@router.post("/refresh", response_model=Token)
async def refresh(
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    refresh_token = request.cookies.get("refresh_token")
    if not refresh_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="未提供刷新凭据")

    payload = decode_token(refresh_token, expected_type="refresh")
    user_id = payload["sub"]
    old_jti = payload["jti"]

    # 检查 refresh jti 黑名单
    from app.core.ratelimit import get_redis

    try:
        r = await get_redis()
        if await r.exists(f"{BLACKLIST_PREFIX_REFRESH}{old_jti}"):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="刷新凭据已失效")
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="认证服务暂不可用")

    # 校验用户状态
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="用户不存在或已禁用")

    # 轮换：旧 refresh jti 先加入黑名单（失败则 503，不签发新 token）
    expire_ts = payload.get("exp", 0)
    now_ts = int(datetime.now(timezone.utc).timestamp())
    ttl = max(expire_ts - now_ts, 1)
    await blacklist_token(old_jti, BLACKLIST_PREFIX_REFRESH, ttl, user_id)

    # 旧 refresh 已撤销，签发新 token
    new_access, _ = create_access_token(user_id)
    new_refresh, _, max_age = create_refresh_token(user_id)
    set_refresh_cookie(response, new_refresh, max_age)

    return Token(access_token=new_access, user=UserOut.model_validate(user))


@router.post("/logout")
async def logout(
    request: Request,
    response: Response,
):
    access_failed = False
    refresh_failed = False

    # 撤销 access token
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        try:
            payload = decode_token(auth_header[7:], expected_type="access")
            expire_ts = payload.get("exp", 0)
            now_ts = int(datetime.now(timezone.utc).timestamp())
            ttl = max(expire_ts - now_ts, 1)
            await blacklist_token(payload["jti"], BLACKLIST_PREFIX_ACCESS, ttl, payload["sub"])
        except HTTPException as e:
            if e.status_code == 503:
                access_failed = True
            # 401 (token 无效) 忽略，503 (Redis 挂) 标记
        except Exception:
            pass  # token decode 失败忽略

    # 撤销 refresh token
    refresh_token = request.cookies.get("refresh_token")
    if refresh_token:
        try:
            payload = decode_token(refresh_token, expected_type="refresh")
            expire_ts = payload.get("exp", 0)
            now_ts = int(datetime.now(timezone.utc).timestamp())
            ttl = max(expire_ts - now_ts, 1)
            await blacklist_token(payload["jti"], BLACKLIST_PREFIX_REFRESH, ttl, payload["sub"])
        except HTTPException as e:
            if e.status_code == 503:
                refresh_failed = True
        except Exception:
            pass

    if access_failed or refresh_failed:
        clear_refresh_cookie(response)
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="认证服务暂不可用")

    clear_refresh_cookie(response)
    return {"detail": "已退出登录"}


# ---------- SSO/OIDC 预留 ----------


@router.get("/sso/providers")
async def sso_providers():
    """返回可用的 SSO 提供商列表"""
    return {
        "providers": [
            {
                "id": "oidc",
                "name": "OIDC",
                "enabled": False,
                "login_url": None,
            }
        ]
    }


@router.get("/sso/oidc/login")
async def sso_oidc_login():
    """OIDC 登录入口（未配置）"""
    raise HTTPException(status_code=501, detail="OIDC 未配置")
