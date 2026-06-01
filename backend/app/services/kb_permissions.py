"""知识库权限判断工具函数"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.kb_member import KnowledgeBaseMember
from app.models.knowledge_base import KnowledgeBase
from app.models.user import User


async def get_kb_role(db: AsyncSession, user: User, kb: KnowledgeBase) -> str | None:
    """获取用户在知识库中的角色，admin 返回 'admin'，无角色返回 None"""
    if user.role == "admin":
        return "admin"

    result = await db.execute(
        select(KnowledgeBaseMember.role).where(
            KnowledgeBaseMember.knowledge_base_id == kb.id,
            KnowledgeBaseMember.user_id == user.id,
        )
    )
    role = result.scalar_one_or_none()
    if role:
        return role

    # 兼容旧数据：created_by 视为 owner
    if kb.created_by == user.id:
        return "owner"

    return None


async def can_view_kb(db: AsyncSession, user: User, kb: KnowledgeBase) -> bool:
    """用户是否可以查看知识库"""
    role = await get_kb_role(db, user, kb)
    return role is not None


async def can_edit_kb(db: AsyncSession, user: User, kb: KnowledgeBase) -> bool:
    """用户是否可以编辑知识库内容（上传、重试索引等）"""
    role = await get_kb_role(db, user, kb)
    return role in ("owner", "editor", "admin")


async def can_manage_kb(db: AsyncSession, user: User, kb: KnowledgeBase) -> bool:
    """用户是否可以管理知识库（修改、删除、成员管理）"""
    role = await get_kb_role(db, user, kb)
    return role in ("owner", "admin")
