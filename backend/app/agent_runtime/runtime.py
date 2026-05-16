from app.agent_runtime.graph import build_agent_graph
from app.agent_runtime.schemas import AgentState
from app.agent_runtime.tools import ToolContext, ToolRegistry


class AgentRuntime:
    """LangGraph Agent Runtime 对外封装。"""

    def __init__(self, tool_registry: ToolRegistry, max_steps: int = 8):
        self.tool_registry = tool_registry
        self.max_steps = max_steps
        self.graph = build_agent_graph(tool_registry)

    async def run(self, goal: str, ctx: ToolContext, history: list[dict] | None = None) -> AgentState:
        initial_state = AgentState(
            goal=goal,
            session_id=ctx.session_id,
            user_id=ctx.user_id,
            max_steps=self.max_steps,
            history=history or [],
        )
        config = {"configurable": {"thread_id": initial_state.run_id}}
        result = await self.graph.ainvoke(
            {
                "goal": goal,
                "ctx": ctx,
                "runtime_state": initial_state,
                "tool_registry": self.tool_registry,
            },
            config=config,
        )
        return result["runtime_state"]
