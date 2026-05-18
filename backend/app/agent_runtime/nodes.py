import time
from typing import Any, TypedDict

from app.agent_runtime.planner import RuleBasedPlanner
from app.agent_runtime.schemas import AgentAction, AgentObservation, AgentState, AgentStep
from app.agent_runtime.tools import ToolContext, ToolRegistry
from app.core.metrics import agent_step_duration_seconds, agent_steps_total, agent_tool_calls_total


class GraphState(TypedDict, total=False):
    goal: str
    ctx: ToolContext
    runtime_state: AgentState
    next_action: AgentAction
    finished: bool
    route: str
    tool_registry: ToolRegistry
    seen_actions: set[str]


def perceive_node(state: GraphState) -> dict[str, Any]:
    runtime_state = state.get("runtime_state")
    if not runtime_state:
        ctx = state["ctx"]
        runtime_state = AgentState(
            goal=state["goal"],
            session_id=ctx.session_id,
            user_id=ctx.user_id,
        )
    return {
        "runtime_state": runtime_state,
        "finished": runtime_state.finished,
        "seen_actions": state.get("seen_actions", set()),
    }


def plan_node(state: GraphState) -> dict[str, Any]:
    runtime_state = state["runtime_state"]
    registry = state["tool_registry"]
    planner = RuleBasedPlanner()
    available_tools = [tool["name"] for tool in registry.list_tools()]
    action = planner.next_action(runtime_state, available_tools)
    return {"next_action": action}


def tool_router_node(state: GraphState) -> dict[str, Any]:
    action = state["next_action"]
    if action.action_type == "tool":
        return {"route": "tool_executor"}
    return {"route": "finish"}


async def tool_executor_node(state: GraphState) -> dict[str, Any]:
    runtime_state = state["runtime_state"]
    action = state["next_action"]
    registry = state["tool_registry"]
    ctx = state["ctx"]

    runtime_state.step_index += 1
    seen_actions = state.get("seen_actions", set())
    signature = f"{action.tool_name}:{action.arguments}"
    if signature in seen_actions:
        runtime_state.finished = True
        runtime_state.failure_reason = "检测到重复工具调用，已停止执行。"
        runtime_state.steps.append(
            AgentStep(
                index=runtime_state.step_index,
                phase="finish",
                thought=runtime_state.failure_reason,
                action=action,
            )
        )
        return {
            "runtime_state": runtime_state,
            "route": "finish",
            "finished": True,
            "seen_actions": seen_actions,
        }
    seen_actions.add(signature)

    started = time.time()
    result = await registry.call(action.tool_name or "", action.arguments, ctx)
    latency_ms = int((time.time() - started) * 1000)

    # 记录指标
    agent_steps_total.labels(phase="act").inc()
    agent_tool_calls_total.labels(tool=action.tool_name or "unknown", status=result.status).inc()
    agent_step_duration_seconds.labels(phase="act").observe(latency_ms / 1000)

    observation = AgentObservation(
        status="ok" if result.status == "ok" else "error",
        content=result.content,
        data=result.data,
        error=result.error,
    )
    runtime_state.observations.append(observation)
    runtime_state.steps.append(
        AgentStep(
            index=runtime_state.step_index,
            phase="act",
            thought=action.reason,
            action=action,
            observation=observation,
            latency_ms=latency_ms,
        )
    )
    return {"runtime_state": runtime_state, "seen_actions": seen_actions}


def reflect_node(state: GraphState) -> dict[str, Any]:
    runtime_state = state["runtime_state"]
    if runtime_state.finished:
        return {"runtime_state": runtime_state, "route": "finish", "finished": True}

    max_steps = runtime_state.max_steps
    if runtime_state.step_index >= max_steps:
        runtime_state.finished = True
        runtime_state.failure_reason = f"达到最大步数 {max_steps}，已停止执行。"
        return {"runtime_state": runtime_state, "route": "finish", "finished": True}
    return {"runtime_state": runtime_state, "route": "plan", "finished": False}


def finish_node(state: GraphState) -> dict[str, Any]:
    runtime_state = state["runtime_state"]
    action = state.get("next_action")

    if action and action.action_type == "finish":
        runtime_state.finished = True
        runtime_state.final_answer = action.final_answer
        runtime_state.steps.append(
            AgentStep(
                index=runtime_state.step_index + 1,
                phase="finish",
                thought=action.reason,
                action=action,
            )
        )
    elif action and action.action_type == "clarify":
        runtime_state.finished = True
        runtime_state.clarify_question = action.question
        runtime_state.steps.append(
            AgentStep(
                index=runtime_state.step_index + 1,
                phase="finish",
                thought=action.reason,
                action=action,
            )
        )
    elif action and action.action_type == "fail":
        runtime_state.finished = True
        runtime_state.failure_reason = action.reason
        runtime_state.steps.append(
            AgentStep(
                index=runtime_state.step_index + 1,
                phase="finish",
                thought=action.reason,
                action=action,
            )
        )
    else:
        runtime_state.finished = True

    return {"runtime_state": runtime_state, "finished": True}


def route_after_router(state: GraphState) -> str:
    return state["route"]


def route_after_reflect(state: GraphState) -> str:
    return state["route"]
