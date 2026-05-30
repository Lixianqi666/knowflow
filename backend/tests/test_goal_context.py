"""目标上下文注入和目标状态更新测试"""

import json
from unittest.mock import AsyncMock, patch

import pytest

from app.core.prompts import build_messages, format_goal_context


def test_format_goal_context_basic():
    result = format_goal_context(goal="制定营销方案")
    assert "制定营销方案" in result
    assert "暂无进展" in result
    assert "无" in result
    assert "<goal_context>" in result
    assert "</goal_context>" in result


def test_format_goal_context_with_details():
    result = format_goal_context(
        goal="制定营销方案",
        goal_summary="已确定目标受众",
        missing_info=["预算范围", "时间周期"],
    )
    assert "已确定目标受众" in result
    assert "预算范围" in result
    assert "时间周期" in result


def test_goal_context_injected_in_messages():
    goal_ctx = format_goal_context(goal="测试目标")
    messages = build_messages(
        system="你是助手",
        history=[],
        question="你好",
        goal_context=goal_ctx,
    )
    sys_content = messages[0]["content"]
    assert "测试目标" in sys_content
    assert "<goal_context>" in sys_content


def test_goal_context_not_in_retrieved_docs():
    """goal_context 和 retrieved_documents 是分开的"""
    goal_ctx = format_goal_context(goal="我的目标")
    messages = build_messages(
        system="你是助手。检索内容：{context}",
        context="<retrieved_documents>文档内容</retrieved_documents>",
        history=[],
        question="问题",
        goal_context=goal_ctx,
    )
    sys_content = messages[0]["content"]
    # 两个边界都存在
    assert "<goal_context>" in sys_content
    assert "<retrieved_documents>" in sys_content
    # goal 不在 retrieved_documents 内
    goal_pos = sys_content.index("<goal_context>")
    docs_pos = sys_content.index("<retrieved_documents>")
    assert goal_pos != docs_pos


def test_no_goal_context_when_none():
    messages = build_messages(
        system="你是助手",
        history=[],
        question="你好",
        goal_context=None,
    )
    assert "<goal_context>" not in messages[0]["content"]


@pytest.mark.asyncio
async def test_update_goal_state_success():
    """update_goal_state 正常更新"""
    from app.services.chat import ChatService

    mock_db = AsyncMock()
    service = ChatService(mock_db)

    mock_conv = type("Conv", (), {
        "goal": "制定方案",
        "goal_summary": None,
        "missing_info": [],
        "goal_status": "active",
    })()

    mock_llm_response = json.dumps({
        "goal_summary": "已确定方向",
        "missing_info": ["预算"],
        "goal_status": "active",
    })

    with patch("app.services.chat.llm_service") as mock_llm:
        mock_llm.complete = AsyncMock(return_value=mock_llm_response)
        await service._update_goal_state(mock_conv, "用户消息", "助手回复", [])

    assert mock_conv.goal_summary == "已确定方向"
    assert mock_conv.missing_info == ["预算"]
    assert mock_conv.goal_status == "active"


@pytest.mark.asyncio
async def test_update_goal_state_invalid_json():
    """LLM 返回非法 JSON 不影响主流程"""
    from app.services.chat import ChatService

    mock_db = AsyncMock()
    service = ChatService(mock_db)

    mock_conv = type("Conv", (), {
        "goal": "制定方案",
        "goal_summary": "原始摘要",
        "missing_info": [],
        "goal_status": "active",
    })()

    with patch("app.services.chat.llm_service") as mock_llm:
        mock_llm.complete = AsyncMock(return_value="这不是JSON")
        # 不应抛出异常
        await service._update_goal_state(mock_conv, "用户消息", "助手回复", [])

    # 状态保持不变
    assert mock_conv.goal_summary == "原始摘要"
    assert mock_conv.goal_status == "active"


@pytest.mark.asyncio
async def test_update_goal_state_partial_json():
    """LLM 返回部分字段只更新有效字段"""
    from app.services.chat import ChatService

    mock_db = AsyncMock()
    service = ChatService(mock_db)

    mock_conv = type("Conv", (), {
        "goal": "制定方案",
        "goal_summary": "旧摘要",
        "missing_info": ["旧信息"],
        "goal_status": "active",
    })()

    mock_llm_response = json.dumps({
        "goal_summary": "新摘要",
        # 缺少 missing_info 和 goal_status
    })

    with patch("app.services.chat.llm_service") as mock_llm:
        mock_llm.complete = AsyncMock(return_value=mock_llm_response)
        await service._update_goal_state(mock_conv, "用户消息", "助手回复", [])

    assert mock_conv.goal_summary == "新摘要"
    # missing_info 未在响应中，保持不变
    assert mock_conv.missing_info == ["旧信息"]
    assert mock_conv.goal_status == "active"


@pytest.mark.asyncio
async def test_update_goal_state_invalid_status():
    """非法 goal_status 值不更新"""
    from app.services.chat import ChatService

    mock_db = AsyncMock()
    service = ChatService(mock_db)

    mock_conv = type("Conv", (), {
        "goal": "制定方案",
        "goal_summary": None,
        "missing_info": [],
        "goal_status": "active",
    })()

    mock_llm_response = json.dumps({
        "goal_status": "invalid_status",
    })

    with patch("app.services.chat.llm_service") as mock_llm:
        mock_llm.complete = AsyncMock(return_value=mock_llm_response)
        await service._update_goal_state(mock_conv, "用户消息", "助手回复", [])

    assert mock_conv.goal_status == "active"
