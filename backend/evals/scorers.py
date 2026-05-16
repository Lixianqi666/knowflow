def tool_selection_accuracy(actual: list[str], expected: list[str]) -> float:
    if not expected:
        return 1.0 if not actual else 0.0
    matched = sum(1 for tool in expected if tool in actual)
    return matched / len(expected)


def trajectory_score(steps: list[dict]) -> float:
    if not steps:
        return 0.0
    score = 1.0
    seen = set()
    for step in steps:
        action = step.get("action") or {}
        tool_name = action.get("tool_name")
        arguments = action.get("arguments") or {}
        signature = f"{tool_name}:{arguments}"
        if tool_name and signature in seen:
            score -= 0.3
        seen.add(signature)
        observation = step.get("observation") or {}
        if observation.get("status") == "error" and tool_name == "submit_reimbursement":
            score -= 0.2
    return max(score, 0.0)


def score_task(case: dict, result: dict) -> dict:
    final_text = result.get("final_text") or ""
    status_ok = result.get("status") == case.get("expected_status")
    text_ok = all(word in final_text for word in case.get("must_include", []))
    actual_tools = [
        step.get("action", {}).get("tool_name")
        for step in result.get("steps", [])
        if step.get("action", {}).get("tool_name")
    ]
    tool_score = tool_selection_accuracy(actual_tools, case.get("expected_tools", []))
    trace_score = trajectory_score(result.get("steps", []))
    return {
        "success": bool(status_ok and text_ok),
        "tool_selection_accuracy": tool_score,
        "trajectory_score": trace_score,
        "steps": len(result.get("steps", [])),
    }
