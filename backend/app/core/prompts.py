from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from pydantic import BaseModel, Field


class RAGResponse(BaseModel):
    """RAG 问答结构化输出"""

    answer: str = Field(description="基于文档的回答，markdown 格式")
    sources: list[str] = Field(description="引用的文档标题列表")
    confidence: str = Field(description="置信度: high/medium/low")
    has_sufficient_context: bool = Field(description="检索到的内容是否足以回答问题")


rag_parser = PydanticOutputParser(pydantic_object=RAGResponse)

RAG_PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            """你是一个企业内部知识库助手。严格按以下规则回答：

1. 只基于下方「检索到的文档内容」回答，不要编造或推测文档中没有的信息
2. 回答要准确、简洁、有条理，使用 markdown 格式，允许适当使用列表和表格
3. 必须在回答末尾引用来源，格式：[来源: 文档标题]

检索到的文档内容：
{context}""",
        ),
        MessagesPlaceholder("history"),
        ("human", "{question}"),
    ]
)

NO_CONTEXT_PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            """你是一个企业内部知识库助手。本次检索未找到与用户问题相关的文档内容。
请礼貌告知用户未找到相关信息，建议换个关键词或确认文档是否已上传。
不要编造任何信息。""",
        ),
        MessagesPlaceholder("history"),
        ("human", "{question}"),
    ]
)
