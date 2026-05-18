import inspect
from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable

from pydantic import BaseModel, Field


class ToolContext(BaseModel):
    """工具调用上下文。"""

    user_id: str
    session_id: str | None = None
    is_admin: bool = False
    db: Any | None = None


class ToolResult(BaseModel):
    """工具调用结果。"""

    status: str
    content: str
    data: dict[str, Any] = Field(default_factory=dict)
    error: str | None = None


ToolFunc = Callable[..., ToolResult | Awaitable[ToolResult]]


@dataclass
class ToolSpec:
    name: str
    func: ToolFunc
    description: str
    required_args: list[str] = field(default_factory=list)


class ToolRegistry:
    """统一管理 Agent 可调用工具。"""

    def __init__(self):
        self._tools: dict[str, ToolSpec] = {}

    def register(
        self,
        name: str,
        func: ToolFunc,
        description: str,
        required_args: list[str] | None = None,
    ) -> None:
        self._tools[name] = ToolSpec(
            name=name,
            func=func,
            description=description,
            required_args=required_args or [],
        )

    def list_tools(self) -> list[dict[str, Any]]:
        return [
            {
                "name": spec.name,
                "description": spec.description,
                "required_args": spec.required_args,
            }
            for spec in self._tools.values()
        ]

    async def call(self, name: str, arguments: dict[str, Any], ctx: ToolContext) -> ToolResult:
        spec = self._tools.get(name)
        if not spec:
            return ToolResult(status="error", content=f"未知工具: {name}", error="unknown_tool")

        missing = [arg for arg in spec.required_args if not arguments.get(arg)]
        if missing:
            return ToolResult(
                status="error",
                content=f"缺少参数: {', '.join(missing)}",
                error="missing_arguments",
                data={"missing": missing},
            )

        try:
            result = spec.func(ctx, **arguments)
            if inspect.isawaitable(result):
                result = await result
            return result
        except Exception as e:
            return ToolResult(status="error", content=f"工具调用失败: {e}", error=str(e))
