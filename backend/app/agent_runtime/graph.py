# LangGraph 只负责 Agent 状态流转。
# 当前默认使用无 checkpoint 的编译图；如需长程任务恢复，可在 compile 时传入 InMemorySaver 或持久化 checkpointer。

from langgraph.graph import END, START, StateGraph

from app.agent_runtime.nodes import (
    GraphState,
    finish_node,
    perceive_node,
    plan_node,
    reflect_node,
    route_after_reflect,
    route_after_router,
    tool_executor_node,
    tool_router_node,
)
from app.agent_runtime.tools import ToolRegistry


def build_agent_graph(tool_registry: ToolRegistry):
    """构建 LangGraph Agent 状态图。"""
    graph = StateGraph(GraphState)
    graph.add_node("perceive", perceive_node)
    graph.add_node("plan", plan_node)
    graph.add_node("tool_router", tool_router_node)
    graph.add_node("tool_executor", tool_executor_node)
    graph.add_node("reflect", reflect_node)
    graph.add_node("finish", finish_node)

    graph.add_edge(START, "perceive")
    graph.add_edge("perceive", "plan")
    graph.add_edge("plan", "tool_router")
    graph.add_conditional_edges(
        "tool_router",
        route_after_router,
        {"tool_executor": "tool_executor", "finish": "finish"},
    )
    graph.add_edge("tool_executor", "reflect")
    graph.add_conditional_edges(
        "reflect",
        route_after_reflect,
        {"plan": "plan", "finish": "finish"},
    )
    graph.add_edge("finish", END)
    return graph.compile()
