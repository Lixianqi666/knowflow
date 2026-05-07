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

1. 只基于下方「检索到的文档内容」回答，不要编造或推测文档中没有的信息
2. 回答要准确、简洁、有条理，使用 markdown 格式，允许适当使用列表和表格
3. 必须在回答末尾引用来源，格式：[来源: 文档标题]
4. 在回答末尾用以下 JSON 格式输出结构化信息（不要加 markdown 代码块包裹）：
```json
{{"answer": "你的回答", "sources": ["文档标题1"], "confidence": "high", "has_sufficient_context": true}}
```

检索到的文档内容：
{context}"""

NO_CONTEXT_SYSTEM = """你是一个企业内部知识库助手。本次检索未找到与用户问题相关的文档内容。
请礼貌告知用户未找到相关信息，建议换个关键词或确认文档是否已上传。
不要编造任何信息。"""


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
