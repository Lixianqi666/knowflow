import pytest

from app.agent_runtime.business_tools import build_business_tool_registry
from app.agent_runtime.tools import ToolContext, ToolRegistry, ToolResult


async def echo_tool(ctx: ToolContext, text: str) -> ToolResult:
    return ToolResult(status="ok", content=text, data={"echo": text})


@pytest.mark.asyncio
async def test_tool_registry_calls_registered_tool():
    registry = ToolRegistry()
    registry.register("echo", echo_tool, description="回显文本", required_args=["text"])

    result = await registry.call("echo", {"text": "hello"}, ToolContext(user_id="u1"))

    assert result.status == "ok"
    assert result.content == "hello"
    assert result.data["echo"] == "hello"


@pytest.mark.asyncio
async def test_tool_registry_rejects_unknown_tool():
    registry = ToolRegistry()

    result = await registry.call("missing", {}, ToolContext(user_id="u1"))

    assert result.status == "error"
    assert "未知工具" in result.content


@pytest.mark.asyncio
async def test_tool_registry_validates_required_args():
    registry = ToolRegistry()
    registry.register("echo", echo_tool, description="回显文本", required_args=["text"])

    result = await registry.call("echo", {}, ToolContext(user_id="u1"))

    assert result.status == "error"
    assert "缺少参数" in result.content


def test_business_tool_registry_contains_required_tools():
    registry = build_business_tool_registry()
    names = {tool["name"] for tool in registry.list_tools()}

    assert "search_policy" in names
    assert "get_employee" in names
    assert "list_receipts" in names
    assert "validate_invoice" in names
    assert "submit_reimbursement" in names
