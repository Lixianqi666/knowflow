import json

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_agent_message_stream_emits_trace(client: AsyncClient, admin_headers: dict, auth_headers: dict):
    agent_resp = await client.post(
        "/api/v1/agents/",
        headers=admin_headers,
        json={"name": "报销助手", "description": "测试", "system_prompt": "", "knowledge_base_ids": []},
    )
    assert agent_resp.status_code == 200
    agent_id = agent_resp.json()["id"]

    session_resp = await client.post(
        f"/api/v1/agents/{agent_id}/sessions",
        headers=auth_headers,
        json={"title": "报销测试"},
    )
    assert session_resp.status_code == 200
    session_id = session_resp.json()["id"]

    async with client.stream(
        "POST",
        f"/api/v1/agents/sessions/{session_id}/messages",
        headers=auth_headers,
        json={"content": "帮张三报销上海出差费用"},
        timeout=30,
    ) as resp:
        events = []
        async for line in resp.aiter_lines():
            if line.startswith("data: "):
                events.append(json.loads(line[6:]))

    assert any(event["type"] == "trace" for event in events)
    assert events[-1]["type"] in ("done", "error")
