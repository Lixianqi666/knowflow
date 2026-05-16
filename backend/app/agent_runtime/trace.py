from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.agent_runtime.schemas import AgentStep
from app.models.agent_trace import AgentStepTrace


def step_to_event(step: AgentStep) -> dict:
    """将 AgentStep 转为 SSE trace 事件。"""
    return {
        "type": "trace",
        "data": {
            "step_index": step.index,
            "phase": step.phase,
            "thought": step.thought,
            "action": step.action.model_dump() if step.action else None,
            "observation": step.observation.model_dump() if step.observation else None,
            "latency_ms": step.latency_ms,
            "tokens": step.tokens,
        },
    }


async def persist_step(db: AsyncSession, run_id: str | UUID, step: AgentStep) -> None:
    """持久化单步轨迹。"""
    trace = AgentStepTrace(
        run_id=run_id,
        step_index=step.index,
        phase=step.phase,
        thought=step.thought,
        action=step.action.model_dump() if step.action else {},
        observation=step.observation.model_dump() if step.observation else {},
        latency_ms=step.latency_ms,
        tokens=step.tokens,
        error=step.observation.error if step.observation else None,
    )
    db.add(trace)
    await db.flush()
