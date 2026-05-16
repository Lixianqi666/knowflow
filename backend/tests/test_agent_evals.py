from evals.scorers import score_task, tool_selection_accuracy, trajectory_score


def test_tool_selection_accuracy():
    actual = ["search_policy", "get_employee", "list_receipts"]
    expected = ["search_policy", "get_employee", "submit_reimbursement"]

    score = tool_selection_accuracy(actual, expected)

    assert round(score, 2) == 0.67


def test_trajectory_score_penalizes_repeated_actions():
    steps = [
        {"action": {"tool_name": "submit_reimbursement", "arguments": {"employee_name": "张三"}}},
        {"action": {"tool_name": "submit_reimbursement", "arguments": {"employee_name": "张三"}}},
    ]

    score = trajectory_score(steps)

    assert score < 1


def test_score_task_checks_status_and_text():
    case = {"expected_status": "clarify", "must_include": ["员工"]}
    result = {"status": "clarify", "final_text": "请提供员工姓名", "steps": []}

    score = score_task(case, result)

    assert score["success"] is True
