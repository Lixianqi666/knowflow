import json
from pathlib import Path


def summarize(results: list[dict]) -> dict:
    total = len(results)
    if total == 0:
        return {
            "task_success_rate": 0,
            "avg_steps": 0,
            "tool_selection_accuracy": 0,
            "trajectory_score": 0,
        }
    return {
        "task_success_rate": sum(1 for r in results if r["score"]["success"]) / total,
        "avg_steps": sum(r["score"]["steps"] for r in results) / total,
        "tool_selection_accuracy": sum(r["score"]["tool_selection_accuracy"] for r in results) / total,
        "trajectory_score": sum(r["score"]["trajectory_score"] for r in results) / total,
    }


def write_report(path: str, results: list[dict]) -> None:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    summary = summarize(results)
    data = {"summary": summary, "results": results}
    output.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    md_path = output.with_suffix(".md")
    lines = [
        "# Agent Eval Report",
        "",
        f"- 任务成功率：{summary['task_success_rate']:.2%}",
        f"- 平均步数：{summary['avg_steps']:.2f}",
        f"- 工具选择准确率：{summary['tool_selection_accuracy']:.2%}",
        f"- 轨迹质量：{summary['trajectory_score']:.2f}",
        "",
        "| Case | Success | Steps | Tool Accuracy | Trajectory |",
        "|---|---:|---:|---:|---:|",
    ]
    for item in results:
        score = item["score"]
        lines.append(
            f"| {item['id']} | {score['success']} | {score['steps']} | {score['tool_selection_accuracy']:.2f} | {score['trajectory_score']:.2f} |"
        )
    md_path.write_text("\n".join(lines), encoding="utf-8")
