from app.agent_runtime.schemas import AgentAction, AgentObservation, AgentState, AgentStep


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
