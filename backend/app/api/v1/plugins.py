from fastapi import APIRouter, Depends

from app.core.deps import get_current_admin
from app.core.plugins import list_plugins
from app.models.user import User

router = APIRouter(prefix="/plugins", tags=["插件"])


@router.get("/")
async def get_plugins(admin: User = Depends(get_current_admin)):
    return {"plugins": list_plugins()}
