import pytest

from app.agent_runtime.graph import build_agent_graph
from app.agent_runtime.memory import ShortTermMemory
from app.agent_runtime.planner import RuleBasedPlanner
from app.agent_runtime.runtime import AgentRuntime
from app.agent_runtime.schemas import AgentAction, AgentObservation, AgentState, AgentStep
from app.agent_runtime.tools import ToolContext, ToolRegistry, ToolResult
from app.agent_runtime.trace import step_to_event


def test_agent_state_defaults():
    state = AgentState(goal="帮张三提交差旅报销")
    assert state.goal == "帮张三提交差旅报销"
    assert state.step_index == 0
    assert state.max_steps == 8
    assert state.history == []
    assert state.observations == []
    assert state.finished is False


def test_agent_action_requires_tool_when_type_is_tool():
    action = AgentAction(
        action_type="tool", tool_name="search_policy", arguments={"query": "差旅报销"}
    )
    assert action.tool_name == "search_policy"
    assert action.arguments["query"] == "差旅报销"


def test_agent_step_records_action_and_observation():
    action = AgentAction(action_type="tool", tool_name="search_policy", arguments={"query": "发票"})
    observation = AgentObservation(status="ok", content="需要发票", data={"matched": True})
    step = AgentStep(index=1, phase="act", action=action, observation=observation, latency_ms=12)
    assert step.index == 1
    assert step.observation.status == "ok"
    assert step.latency_ms == 12


def test_short_term_memory_limits_recent_messages():
    memory = ShortTermMemory(max_messages=3)
    rows = [
        {"role": "user", "content": "m1"},
        {"role": "assistant", "content": "m2"},
        {"role": "user", "content": "m3"},
        {"role": "assistant", "content": "m4"},
    ]

    result = memory.select(rows)

    assert [m["content"] for m in result] == ["m2", "m3", "m4"]


def test_step_to_event_serializes_trace():
    action = AgentAction(action_type="tool", tool_name="search_policy", arguments={"query": "报销"})
    observation = AgentObservation(status="ok", content="找到政策")
    step = AgentStep(
        index=1, phase="act", thought="需要查政策", action=action, observation=observation
    )

    event = step_to_event(step)

    assert event["type"] == "trace"
    assert event["data"]["step_index"] == 1
    assert event["data"]["action"]["tool_name"] == "search_policy"
    assert event["data"]["observation"]["content"] == "找到政策"


def test_planner_starts_with_policy_search_for_reimbursement():
    planner = RuleBasedPlanner()
    state = AgentState(goal="帮张三报销上海出差费用")

    action = planner.next_action(state, available_tools=["search_policy", "get_employee"])

    assert action.action_type == "tool"
    assert action.tool_name == "search_policy"
    assert "报销" in action.arguments["query"]


def test_planner_clarifies_when_missing_employee():
    planner = RuleBasedPlanner()
    state = AgentState(goal="帮他报销差旅费")

    action = planner.next_action(state, available_tools=["search_policy", "get_employee"])

    assert action.action_type == "clarify"
    assert "员工" in action.question


async def done_tool(ctx: ToolContext, **kwargs):
    return ToolResult(status="ok", content="申请已提交", data={"request_id": "R001"})


def test_build_agent_graph_returns_compiled_graph():
    registry = ToolRegistry()
    graph = build_agent_graph(registry)

    assert hasattr(graph, "invoke")


@pytest.mark.asyncio
async def test_langgraph_runtime_records_tool_step():
    registry = ToolRegistry()
    registry.register("search_policy", done_tool, description="查询政策")
    runtime = AgentRuntime(tool_registry=registry, max_steps=1)

    result = await runtime.run(goal="帮张三报销上海出差费用", ctx=ToolContext(user_id="u1"))

    assert len(result.steps) == 1
    assert result.steps[0].action.tool_name == "search_policy"
    assert result.steps[0].observation.content == "申请已提交"


@pytest.mark.asyncio
async def test_langgraph_runtime_stops_at_max_steps():
    registry = ToolRegistry()
    registry.register("search_policy", done_tool, description="查询政策")
    runtime = AgentRuntime(tool_registry=registry, max_steps=1)

    result = await runtime.run(goal="帮张三报销上海出差费用", ctx=ToolContext(user_id="u1"))

    assert result.finished is True
    assert len(result.steps) <= 1


@pytest.mark.asyncio
async def test_langgraph_runtime_detects_repeated_action():
    registry = ToolRegistry()
    registry.register("search_policy", done_tool, description="查询政策")
    runtime = AgentRuntime(tool_registry=registry, max_steps=3)

    result = await runtime.run(goal="普通问题", ctx=ToolContext(user_id="u1"))

    assert result.finished is True
    assert len(result.steps) <= 3


@pytest.mark.asyncio
async def test_langgraph_runtime_keeps_run_id():
    registry = ToolRegistry()
    runtime = AgentRuntime(tool_registry=registry, max_steps=1)

    result = await runtime.run(goal="帮他报销差旅费", ctx=ToolContext(user_id="u1"))

    assert result.run_id
    assert result.finished is True
