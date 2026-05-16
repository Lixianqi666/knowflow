# KnowFlow Agent 面试挑战

## 背景

KnowFlow 是企业知识库 RAG 平台。你的任务是将现有 RAG Assistant 升级为具备规划、工具调用、记忆、反馈闭环和量化评估的业务 Agent。

## 候选人任务

1. 阅读 `backend/app/agent_runtime`。
2. 提升 `backend/evals/datasets/travel_reimbursement.jsonl` 的任务成功率。
3. 降低平均步数和无效工具调用。
4. 增强异常处理和轨迹记录。
5. 说明如果成功率卡在 80%，下一步如何优化。

## 运行方式

```bash
cd backend
python -m evals.runner --dataset evals/datasets/travel_reimbursement.jsonl --out evals/reports/latest.json
```

## 交付物

- 代码改动。
- eval 报告。
- 关键设计说明。
