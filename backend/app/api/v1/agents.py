import json
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agent_runtime.business_tools import build_business_tool_registry
from app.agent_runtime.runtime import AgentRuntime
from app.agent_runtime.tools import ToolContext
from app.agent_runtime.trace import step_to_event
from app.core.deps import get_current_admin
from app.core.security import get_current_user
from app.database import async_session, get_db
from app.models.agent import Agent
from app.models.agent_session import AgentMessage, AgentSession
from app.models.user import User

router = APIRouter(prefix="/agents", tags=["Agent 应用"])


# ---------- Schemas ----------


class AgentCreate(BaseModel):
    name: str
    description: str = ""
    system_prompt: str = ""
    knowledge_base_ids: list[str] = []
    top_k: int = 5
    threshold: int = 30
    rerank_top_k: int = 3


class AgentUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    system_prompt: str | None = None
    knowledge_base_ids: list[str] | None = None
    top_k: int | None = None
    threshold: int | None = None
    rerank_top_k: int | None = None
    is_active: bool | None = None


class SessionCreate(BaseModel):
    title: str = "新会话"


class SessionUpdate(BaseModel):
    title: str


class MessageCreate(BaseModel):
    content: str


class MessageRatingCreate(BaseModel):
    rating: int  # 1=赞, -1=踩


# ---------- Agent 管理 (管理员) ----------


@router.get("/admin-list")
async def list_all_agents(
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Agent).order_by(Agent.created_at.desc()))
    return [
        {
            "id": str(a.id),
            "name": a.name,
            "description": a.description,
            "system_prompt": a.system_prompt,
            "knowledge_base_ids": a.knowledge_base_ids,
            "top_k": a.top_k,
            "threshold": a.threshold,
            "rerank_top_k": a.rerank_top_k,
            "is_active": a.is_active,
            "created_at": str(a.created_at),
        }
        for a in result.scalars().all()
    ]


@router.post("/")
async def create_agent(
    data: AgentCreate,
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    agent = Agent(
        name=data.name,
        description=data.description,
        system_prompt=data.system_prompt,
        knowledge_base_ids=data.knowledge_base_ids,
        top_k=data.top_k,
        threshold=data.threshold,
        rerank_top_k=data.rerank_top_k,
        created_by=admin.id,
    )
    db.add(agent)
    await db.flush()
    return {"id": str(agent.id), "name": agent.name}


@router.patch("/{agent_id}")
async def update_agent(
    agent_id: UUID,
    data: AgentUpdate,
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    agent = await db.get(Agent, agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent 不存在")
    if data.name is not None:
        agent.name = data.name
    if data.description is not None:
        agent.description = data.description
    if data.system_prompt is not None:
        agent.system_prompt = data.system_prompt
    if data.knowledge_base_ids is not None:
        agent.knowledge_base_ids = data.knowledge_base_ids
    if data.top_k is not None:
        agent.top_k = data.top_k
    if data.threshold is not None:
        agent.threshold = data.threshold
    if data.rerank_top_k is not None:
        agent.rerank_top_k = data.rerank_top_k
    if data.is_active is not None:
        agent.is_active = data.is_active
    await db.flush()
    return {"id": str(agent.id), "name": agent.name}


@router.delete("/{agent_id}")
async def delete_agent(
    agent_id: UUID,
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    agent = await db.get(Agent, agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent 不存在")
    agent.is_active = False  # 软删除
    await db.flush()
    return {"detail": "已停用"}


# ---------- Agent 使用 (所有用户) ----------


@router.get("/")
async def list_active_agents(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Agent).where(Agent.is_active.is_(True)).order_by(Agent.created_at.desc())
    )
    return [
        {
            "id": str(a.id),
            "name": a.name,
            "description": a.description,
            "top_k": a.top_k,
            "threshold": a.threshold,
        }
        for a in result.scalars().all()
    ]


@router.get("/{agent_id}")
async def get_agent(
    agent_id: UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    agent = await db.get(Agent, agent_id)
    if not agent or not agent.is_active:
        raise HTTPException(status_code=404, detail="Agent 不存在")
    return {
        "id": str(agent.id),
        "name": agent.name,
        "description": agent.description,
        "system_prompt": agent.system_prompt,
        "knowledge_base_ids": agent.knowledge_base_ids,
        "top_k": agent.top_k,
        "threshold": agent.threshold,
        "rerank_top_k": agent.rerank_top_k,
        "is_active": agent.is_active,
    }


# ---------- 会话管理 ----------


@router.post("/{agent_id}/sessions")
async def create_session(
    agent_id: UUID,
    data: SessionCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    agent = await db.get(Agent, agent_id)
    if not agent or not agent.is_active:
        raise HTTPException(status_code=404, detail="Agent 不存在")
    session = AgentSession(agent_id=agent_id, user_id=user.id, title=data.title)
    db.add(session)
    await db.flush()
    return {"id": str(session.id), "agent_id": str(session.agent_id), "title": session.title}


@router.get("/{agent_id}/sessions")
async def list_sessions(
    agent_id: UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    agent = await db.get(Agent, agent_id)
    if not agent or not agent.is_active:
        raise HTTPException(status_code=404, detail="Agent 不存在")
    result = await db.execute(
        select(AgentSession)
        .where(AgentSession.agent_id == agent_id, AgentSession.user_id == user.id)
        .order_by(AgentSession.updated_at.desc())
    )
    return [
        {
            "id": str(s.id),
            "agent_id": str(s.agent_id),
            "title": s.title,
            "created_at": str(s.created_at),
        }
        for s in result.scalars().all()
    ]


@router.get("/sessions/{session_id}")
async def get_session(
    session_id: UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    session = await db.get(AgentSession, session_id)
    if not session or session.user_id != user.id:
        raise HTTPException(status_code=404, detail="会话不存在")
    agent = await db.get(Agent, session.agent_id)
    return {
        "id": str(session.id),
        "agent_id": str(session.agent_id),
        "agent_name": agent.name if agent else "",
        "title": session.title,
        "created_at": str(session.created_at),
    }


@router.patch("/sessions/{session_id}")
async def update_session(
    session_id: UUID,
    data: SessionUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    session = await db.get(AgentSession, session_id)
    if not session or session.user_id != user.id:
        raise HTTPException(status_code=404, detail="会话不存在")
    session.title = data.title
    await db.flush()
    return {"id": str(session.id), "title": session.title}


@router.delete("/sessions/{session_id}")
async def delete_session(
    session_id: UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    session = await db.get(AgentSession, session_id)
    if not session or session.user_id != user.id:
        raise HTTPException(status_code=404, detail="会话不存在")
    await db.delete(session)
    return {"detail": "已删除"}


# ---------- 消息管理 ----------


@router.get("/sessions/{session_id}/messages")
async def get_messages(
    session_id: UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    session = await db.get(AgentSession, session_id)
    if not session or session.user_id != user.id:
        raise HTTPException(status_code=404, detail="会话不存在")
    result = await db.execute(
        select(AgentMessage)
        .where(AgentMessage.session_id == session_id)
        .order_by(AgentMessage.created_at)
    )
    return [
        {
            "id": str(m.id),
            "session_id": str(m.session_id),
            "role": m.role,
            "content": m.content,
            "sources": m.sources,
            "rating": m.rating,
            "created_at": str(m.created_at),
        }
        for m in result.scalars().all()
    ]


@router.post("/sessions/{session_id}/messages")
async def send_message(
    session_id: UUID,
    data: MessageCreate,
    user: User = Depends(get_current_user),
):
    async with async_session() as db:
        session = await db.get(AgentSession, session_id)
        if not session or session.user_id != user.id:
            raise HTTPException(status_code=404, detail="会话不存在")

        async def event_stream():
            try:
                registry = build_business_tool_registry()
                runtime = AgentRuntime(tool_registry=registry, max_steps=8)
                ctx = ToolContext(
                    user_id=str(user.id),
                    session_id=str(session_id),
                    is_admin=user.role == "admin",
                    db=db,
                )
                state = await runtime.run(data.content, ctx)

                for step in state.steps:
                    yield f"data: {json.dumps(step_to_event(step), ensure_ascii=False)}\n\n"

                if state.clarify_question:
                    db.add(AgentMessage(session_id=session_id, role="user", content=data.content))
                    db.add(
                        AgentMessage(
                            session_id=session_id,
                            role="assistant",
                            content=state.clarify_question,
                            sources=[],
                        )
                    )
                    yield f"data: {json.dumps({'type': 'token', 'data': state.clarify_question}, ensure_ascii=False)}\n\n"
                elif state.final_answer:
                    db.add(AgentMessage(session_id=session_id, role="user", content=data.content))
                    db.add(
                        AgentMessage(
                            session_id=session_id,
                            role="assistant",
                            content=state.final_answer,
                            sources=[],
                        )
                    )
                    yield f"data: {json.dumps({'type': 'token', 'data': state.final_answer}, ensure_ascii=False)}\n\n"
                elif state.failure_reason:
                    yield f"data: {json.dumps({'type': 'error', 'data': state.failure_reason}, ensure_ascii=False)}\n\n"
                else:
                    yield f"data: {json.dumps({'type': 'error', 'data': 'Agent 未产生有效结果'}, ensure_ascii=False)}\n\n"

                await db.commit()
                yield f"data: {json.dumps({'type': 'done'}, ensure_ascii=False)}\n\n"
            except Exception as e:
                import logging

                logging.getLogger(__name__).exception(f"Agent SSE流异常: {e}")
                await db.rollback()
                error_event = json.dumps(
                    {"type": "error", "data": f"服务内部错误: {e}"},
                    ensure_ascii=False,
                )
                yield f"data: {error_event}\n\n"

        return StreamingResponse(event_stream(), media_type="text/event-stream")


@router.patch("/messages/{msg_id}/rating")
async def rate_message(
    msg_id: UUID,
    data: MessageRatingCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    msg = await db.get(AgentMessage, msg_id)
    if not msg:
        raise HTTPException(status_code=404, detail="消息不存在")
    session = await db.get(AgentSession, msg.session_id)
    if not session or session.user_id != user.id:
        raise HTTPException(status_code=404, detail="消息不存在")
    if data.rating not in (1, -1):
        raise HTTPException(status_code=400, detail="评分必须是 1(赞) 或 -1(踩)")
    msg.rating = data.rating
    await db.flush()
    return {"detail": "已评分", "rating": data.rating}
