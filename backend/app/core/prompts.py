import json
import re

from pydantic import BaseModel, Field


class RAGResponse(BaseModel):
    """RAG 问答结构化输出"""

    answer: str = Field(description="基于文档的回答，markdown 格式")
    sources: list[str] = Field(description="引用的文档标题列表")
    confidence: str = Field(description="置信度: high/medium/low")
    has_sufficient_context: bool = Field(description="检索到的内容是否足以回答问题")


RAG_SYSTEM = """你是一个企业内部知识库助手。严格按以下规则回答：

1. **只基于下方「检索到的文档内容」回答**，这是唯一的知识来源。如果文档中没有提到某方面信息，必须明确说明"文档中未提及此内容"
2. **绝对不要编造、捏造或推测文档中没有的信息**，包括但不限于：具体数字、政策条款、流程步骤、部门名称、日期、联系方式等
3. 如果文档内容不足以完整回答问题，只回答文档中确认有的部分，其余部分说明"未在文档中找到"
4. 回答要准确、简洁、有条理
5. **格式化要求**：
   - 表格数据必须用 Markdown 表格展示（含对齐的表头）
   - 列表用 `-` 无序列表或 `1.` 有序列表
   - 代码片段用行内代码或代码块
   - 合理使用加粗强调关键数据
6. 必须在回答末尾引用来源，格式：[来源: 文档标题]
7. 在回答末尾用以下 JSON 格式输出结构化信息（不要加 markdown 代码块包裹）：
```json
{{"answer": "你的回答", "sources": ["文档标题1"], "confidence": "high", "has_sufficient_context": true}}
```

检索到的文档内容：
{context}"""

NO_CONTEXT_SYSTEM = """你是一个企业内部知识库助手。

**重要：本次检索未找到与用户问题相关的任何文档内容。**

请严格按以下要求回复：
1. **只能回复一句话**，格式为："抱歉，知识库中暂时没有找到关于「[用户问题的关键词]」的相关文档，建议换个关键词试试，或确认相关文档是否已上传。"
2. **绝对不要提供任何信息**，不要尝试回答用户的问题，不要给出任何建议、解释、流程、数字、政策等
3. **不要编造任何内容**，你的知识库中没有相关信息
4. 回复要简洁，不超过 50 个字"""


def build_messages(
    system: str,
    context: str | None = None,
    history: list[dict] | None = None,
    question: str = "",
) -> list[dict]:
    """构造消息列表，替代 ChatPromptTemplate.aformat_messages"""
    sys_content = system.format(context=context) if context else system
    messages = [{"role": "system", "content": sys_content}]
    if history:
        messages.extend(history)
    messages.append({"role": "user", "content": question})
    return messages


def parse_rag_response(text: str) -> RAGResponse | None:
    """从 LLM 回复中提取结构化 JSON，替代 PydanticOutputParser"""
    # 尝试从 ```json ... ``` 或末尾 JSON 中提取
    m = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if not m:
        m = re.search(r"\{[^{}]*\"answer\"[^{}]*\}", text, re.DOTALL)
    if m:
        try:
            data = json.loads(m.group(1))
            return RAGResponse(
                answer=data.get("answer", text),
                sources=data.get("sources", []),
                confidence=data.get("confidence", "medium"),
                has_sufficient_context=data.get("has_sufficient_context", False),
            )
        except (json.JSONDecodeError, KeyError):
            pass
    return None
