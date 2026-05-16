# Agent 失败案例分析题

## Case 1：重复提交

```json
{
  "goal": "帮张三报销上海出差费用",
  "steps": [
    {"action": {"tool_name": "list_receipts"}, "observation": {"content": "找到交通和住宿票据"}},
    {"action": {"tool_name": "submit_reimbursement"}, "observation": {"content": "提交成功 R001"}},
    {"action": {"tool_name": "submit_reimbursement"}, "observation": {"content": "重复提交失败"}}
  ]
}
```

追问：

1. 根因是什么？
2. 如何通过状态机避免重复提交？
3. 如何加入 eval 防止回归？

## Case 2：缺少员工信息

```json
{
  "goal": "帮他报销差旅费",
  "steps": [
    {"action": {"tool_name": "search_policy"}, "observation": {"content": "找到报销政策"}},
    {"action": {"tool_name": "submit_reimbursement"}, "observation": {"content": "缺少员工姓名"}}
  ]
}
```

追问：

1. Agent 应该在哪一步反问？
2. Planner 如何识别关键信息缺失？
3. 如何评分"反问准确率"？
