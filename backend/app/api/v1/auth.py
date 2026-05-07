from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.ratelimit import auth_rate_limit
from app.database import get_db
from app.schemas.user import Token, UserCreate, UserLogin
from app.services.auth import AuthService

router = APIRouter(prefix="/auth", tags=["认证"])


@router.post("/register", response_model=Token)
async def register(
    data: UserCreate, _: None = Depends(auth_rate_limit), db: AsyncSession = Depends(get_db)
):
    return await AuthService(db).register(data)


@router.post("/login", response_model=Token)
async def login(
    data: UserLogin, _: None = Depends(auth_rate_limit), db: AsyncSession = Depends(get_db)
):
    return await AuthService(db).login(data)
