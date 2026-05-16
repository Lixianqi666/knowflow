from datetime import datetime
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, Field, model_validator


ActionType = Literal["tool", "finish", "clarify", "fail"]
ObservationStatus = Literal["ok", "error", "retryable", "not_found"]
StepPhase = Literal["perceive", "plan", "act", "observe", "reflect", "finish"]


class AgentAction(BaseModel):
    """Agent 下一步动作。"""

    action_type: ActionType
    tool_name: str | None = None
    arguments: dict[str, Any] = Field(default_factory=dict)
    final_answer: str | None = None
    question: str | None = None
    reason: str = ""

    @model_validator(mode="after")
    def validate_action(self):
        if self.action_type == "tool" and not self.tool_name:
            raise ValueError("工具动作必须包含 tool_name")
        if self.action_type == "finish" and not self.final_answer:
            raise ValueError("完成动作必须包含 final_answer")
        if self.action_type == "clarify" and not self.question:
            raise ValueError("澄清动作必须包含 question")
        return self


class AgentObservation(BaseModel):
    """工具执行或环境反馈。"""

    status: ObservationStatus
    content: str
    data: dict[str, Any] = Field(default_factory=dict)
    error: str | None = None


class AgentStep(BaseModel):
    """Agent 单步轨迹。"""

    index: int
    phase: StepPhase
    thought: str = ""
    action: AgentAction | None = None
    observation: AgentObservation | None = None
    latency_ms: int = 0
    tokens: int = 0
    created_at: datetime = Field(default_factory=datetime.utcnow)


class AgentState(BaseModel):
    """Agent 运行状态。"""

    run_id: str = Field(default_factory=lambda: str(uuid4()))
    goal: str
    session_id: str | None = None
    user_id: str | None = None
    step_index: int = 0
    max_steps: int = 8
    history: list[dict[str, Any]] = Field(default_factory=list)
    observations: list[AgentObservation] = Field(default_factory=list)
    steps: list[AgentStep] = Field(default_factory=list)
    finished: bool = False
    final_answer: str | None = None
    clarify_question: str | None = None
    failure_reason: str | None = None
