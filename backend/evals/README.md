# Agent Evals

运行差旅报销 Agent 评估：

```bash
cd backend
python -m evals.runner --dataset evals/datasets/travel_reimbursement.jsonl --out evals/reports/latest.json
```

核心指标：

- `task_success_rate`：任务状态是否符合预期。
- `avg_steps`：平均执行步数。
- `tool_selection_accuracy`：期望工具是否被正确选择。
- `trajectory_score`：轨迹是否无重复动作、无越权提交、无无效循环。
- `avg_latency_ms`：平均耗时。
