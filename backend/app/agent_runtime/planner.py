import re

from app.agent_runtime.schemas import AgentAction, AgentState


class RuleBasedPlanner:
    """规则优先的最小 Planner，确保 baseline 稳定。"""

    def next_action(self, state: AgentState, available_tools: list[str]) -> AgentAction:
        goal = state.goal
        observations_text = "\n".join(o.content for o in state.observations)

        if self._looks_like_reimbursement(goal):
            employee = self._extract_employee(goal)
            if not employee:
                return AgentAction(
                    action_type="clarify",
                    question="请提供需要报销的员工姓名或工号。",
                    reason="报销任务缺少员工身份，无法查询员工和票据。",
                )

            if not self._used_tool(state, "search_policy") and "search_policy" in available_tools:
                return AgentAction(
                    action_type="tool",
                    tool_name="search_policy",
                    arguments={"query": "差旅报销 发票 住宿 交通 标准"},
                    reason="先查询报销政策，确定合规要求。",
                )

            if not self._used_tool(state, "get_employee") and "get_employee" in available_tools:
                return AgentAction(
                    action_type="tool",
                    tool_name="get_employee",
                    arguments={"name": employee},
                    reason="查询员工信息和审批关系。",
                )

            if not self._used_tool(state, "list_receipts") and "list_receipts" in available_tools:
                return AgentAction(
                    action_type="tool",
                    tool_name="list_receipts",
                    arguments={"employee_name": employee},
                    reason="查询员工可用票据。",
                )

            if "缺少" in observations_text or "不完整" in observations_text:
                return AgentAction(
                    action_type="clarify",
                    question="当前报销材料不完整，请补充缺失票据或说明是否继续提交。",
                    reason="工具观察显示材料缺失，需要用户补充。",
                )

            # 校验票据（在提交前）
            if (
                not self._used_tool(state, "validate_invoice")
                and "validate_invoice" in available_tools
            ):
                receipt_ids = self._extract_receipt_ids(state)
                if receipt_ids:
                    return AgentAction(
                        action_type="tool",
                        tool_name="validate_invoice",
                        arguments={"receipt_ids": receipt_ids},
                        reason="提交前校验票据合规性。",
                    )

            # 校验失败则反问
            if self._used_tool(state, "validate_invoice") and "校验未通过" in observations_text:
                return AgentAction(
                    action_type="clarify",
                    question="票据校验未通过（日期不一致或信息不完整），请确认是否仍要提交？",
                    reason="票据校验失败，需要用户确认。",
                )

            if (
                not self._used_tool(state, "submit_reimbursement")
                and "submit_reimbursement" in available_tools
            ):
                return AgentAction(
                    action_type="tool",
                    tool_name="submit_reimbursement",
                    arguments={"employee_name": employee, "trip_city": self._extract_city(goal)},
                    reason="政策、员工和票据信息已查询，尝试提交报销申请。",
                )

            return AgentAction(
                action_type="finish",
                final_answer="已完成差旅报销处理。",
                reason="已执行必要步骤。",
            )

        if "search_policy" in available_tools:
            return AgentAction(
                action_type="tool",
                tool_name="search_policy",
                arguments={"query": goal},
                reason="默认先查询知识库。",
            )

        return AgentAction(action_type="fail", reason="没有可用工具处理该目标")

    def _looks_like_reimbursement(self, text: str) -> bool:
        return any(word in text for word in ("报销", "差旅", "发票", "票据"))

    def _extract_employee(self, text: str) -> str | None:
        # 先尝试"帮X报销"模式，X是2-4个中文字符
        match = re.search(r"(?:帮|给)([一-鿿]{2,4})(?:报销|提交|处理)", text)
        if match:
            name = match.group(1)
            if name not in ("他们", "员工", "同事", "他", "她", "我", "我们", "她们"):
                return name
        # 再尝试直接"X报销"模式（排除以"帮"、"给"开头的情况）
        match = re.search(r"([一-鿿]{2,4})(?:报销|提交|处理)", text)
        if match:
            name = match.group(1)
            # 排除包含动词的姓名
            if not any(verb in name for verb in ("帮", "给", "让", "请")):
                if name not in ("他们", "员工", "同事", "他", "她", "我", "我们", "她们"):
                    return name
        return None

    def _extract_city(self, text: str) -> str | None:
        match = re.search(r"([一-鿿]{2,4})(?:出差|差旅)", text)
        if match:
            return match.group(1)
        match = re.search(r"(?:上周|本周|下周)?([一-鿿]{2,4})(?:出差|差旅)", text)
        return match.group(1) if match else None

    def _extract_receipt_ids(self, state: AgentState) -> list[str]:
        for obs in reversed(state.observations):
            receipts = obs.data.get("receipts", [])
            if receipts:
                return [r["id"] for r in receipts]
        return []

    def _used_tool(self, state: AgentState, tool_name: str) -> bool:
        return any(step.action and step.action.tool_name == tool_name for step in state.steps)
