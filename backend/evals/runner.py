import argparse
import asyncio
import json
from pathlib import Path

from app.agent_runtime.business_tools import build_business_tool_registry
from app.agent_runtime.runtime import AgentRuntime
from app.agent_runtime.tools import ToolContext
from app.database import async_session
from evals.report import write_report
from evals.scorers import score_task


def load_cases(path: str) -> list[dict]:
    return [json.loads(line) for line in Path(path).read_text(encoding="utf-8").splitlines() if line.strip()]


def state_to_result(state) -> dict:
    if state.clarify_question:
        status = "clarify"
        final_text = state.clarify_question
    elif state.failure_reason:
        status = "fail"
        final_text = state.failure_reason
    else:
        status = "success"
        final_text = state.final_answer or ""
    return {
        "status": status,
        "final_text": final_text,
        "steps": [
            {
                "action": step.action.model_dump() if step.action else {},
                "observation": step.observation.model_dump() if step.observation else {},
            }
            for step in state.steps
        ],
    }


async def run_case(case: dict) -> dict:
    async with async_session() as db:
        registry = build_business_tool_registry()
        runtime = AgentRuntime(tool_registry=registry, max_steps=case.get("max_steps", 8))
        state = await runtime.run(case["input"], ToolContext(user_id="eval", is_admin=True, db=db))
        result = state_to_result(state)
        score = score_task(case, result)
        return {"id": case["id"], "input": case["input"], "result": result, "score": score}


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    cases = load_cases(args.dataset)
    results = []
    for case in cases:
        results.append(await run_case(case))
    write_report(args.out, results)


if __name__ == "__main__":
    asyncio.run(main())
