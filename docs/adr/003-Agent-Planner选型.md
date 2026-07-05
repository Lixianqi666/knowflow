# ADR-003: Agent Planner 选型 — 规则引擎 vs LLM 驱动

**状态**：已采纳（规则引擎为当前方案，LLM 驱动为演进方向）
**日期**：2026-05

## 背景

KnowFlow 的 Agent 模块使用 LangGraph StateGraph 做 Plan-Act-Reflect 循环。Planner 节点负责决定下一步动作——调哪个工具、传什么参数。Planner 的实现方式直接决定 Agent 的能力和稳定性。

## 候选方案

| 方案 | 决策方式 | 特点 |
|------|---------|------|
| **规则引擎 (RuleBasedPlanner)** | 正则 + if/elif | 可预测、可测试、不幻觉 |
| LLM function-calling | LLM 根据工具描述自主决策 | 通用、灵活、可能幻觉 |
| 混合模式 | 规则兜底 + LLM 增强 | 平衡但复杂 |

## 对比分析

### 1. 可预测性

- **规则引擎**：输入相同，输出一定相同。可以写单元测试覆盖每个分支。
- **LLM 驱动**：同一输入可能产生不同规划。LLM 可能跳过必要步骤、重复调用工具、选择错误工具。

对于差旅报销这种**合规性要求高**的场景，可预测性比灵活性更重要——不能让 Agent "创造性"地跳过票据校验直接提交。

### 2. 调试难度

- **规则引擎**：出问题时看 planner.py 的 if/elif，一目了然。
- **LLM 驱动**：出问题时要分析 LLM 的推理过程，可能是 prompt 不够清晰、工具描述有歧义、温度参数太高。调试链路长。

### 3. 泛化能力

- **规则引擎**：只能处理预定义场景（差旅报销）。新场景需要写新规则。
- **LLM 驱动**：只要工具描述清晰，理论上可以处理任意任务。这是真正的"通用 Agent"。

这是规则引擎最大的劣势——当前只能处理差旅报销一个场景。

### 4. 成本

- **规则引擎**：零 LLM 调用成本（Planner 节点），只在工具执行和最终生成时调用 LLM。
- **LLM 驱动**：每次规划都要调用 LLM，成本和延迟都更高。

### 5. 与 LangGraph 的关系

LangGraph 的条件边（conditional edges）对两种 Planner 都适用，但价值不同：

- **规则引擎**：条件边只是 if/elif 的另一种写法，LangGraph 的价值主要是状态管理和循环检测。
- **LLM 驱动**：条件边的路由逻辑由 LLM 输出决定，LangGraph 的声明式编排让状态流转更清晰。

## 决策

**当前采用规则引擎（RuleBasedPlanner），后续演进为 LLM 驱动。**

## 理由

1. **Baseline 优先**：项目初期优先保证核心链路稳定可用。规则引擎可预测、可测试，不会因为 LLM 幻觉导致 Agent 行为异常。
2. **合规场景要求**：差旅报销涉及财务审批，每一步都必须可审计、可追溯。规则引擎的执行轨迹是确定性的。
3. **LangGraph 保留演进空间**：当前用 LangGraph 做状态编排，后续替换 Planner 不需要改图结构，只改 `plan` 节点的实现。

## 后果

### 正面

- Agent 行为可预测，每个执行轨迹都能复现。
- 零 LLM 规划成本，延迟低。
- 单元测试覆盖率高（`test_agent_runtime.py`）。

### 负面

- 只能处理差旅报销场景，无法泛化。
- 新场景需要写新规则，开发成本高。
- 面试时需要诚实说明"这是 workflow 不是 autonomous agent"。

### 演进计划

当需要支持多场景时，切换为 LLM function-calling 驱动：

```python
# 伪代码 — LLM Planner
class LLMPlanner:
    async def next_action(self, state, tools):
        tool_descriptions = [t.description for t in tools]
        response = await llm.complete(
            f"当前状态: {state}\n可用工具: {tool_descriptions}\n下一步动作?"
        )
        return parse_llm_action(response)
```

保留规则引擎作为 fallback——LLM 规划失败时降级为规则决策。

## 面试话术

> "当前 Planner 是规则引擎，因为差旅报销场景合规性要求高，需要可预测的执行轨迹。但 LangGraph 的状态图编排为后续替换为 LLM 驱动留了空间——只改 plan 节点实现，不动图结构。这是一个工程上的渐进式决策，不是技术能力的限制。"
