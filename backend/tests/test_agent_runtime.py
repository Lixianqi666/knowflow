from app.agent_runtime.memory import ShortTermMemory
from app.agent_runtime.schemas import AgentAction, AgentObservation, AgentState, AgentStep
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
    action = AgentAction(action_type="tool", tool_name="search_policy", arguments={"query": "差旅报销"})
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
    step = AgentStep(index=1, phase="act", thought="需要查政策", action=action, observation=observation)

    event = step_to_event(step)

    assert event["type"] == "trace"
    assert event["data"]["step_index"] == 1
    assert event["data"]["action"]["tool_name"] == "search_policy"
    assert event["data"]["observation"]["content"] == "找到政策"
