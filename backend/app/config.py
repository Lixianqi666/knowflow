import secrets

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # 数据库
    DATABASE_URL: str = "postgresql+asyncpg://knowflow:knowflow@localhost:5432/knowflow"
    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"
    # JWT — 生产环境必须通过环境变量设置，不能用默认值
    SECRET_KEY: str = ""
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440  # 24小时
    # CORS — 逗号分隔的允许来源，空字符串=仅同源
    CORS_ORIGINS: str = "http://localhost:3000"
    # LLM
    LLM_MODEL: str = "gpt-4o-mini"
    LLM_API_KEY: str = ""
    LLM_BASE_URL: str = ""
    # Embedding（可独立配置，小米embedding用不同base URL）
    EMBEDDING_MODEL: str = "text-embedding-3-small"
    EMBEDDING_API_KEY: str = ""
    EMBEDDING_BASE_URL: str = ""
    EMBEDDING_DIM: int = 1024
    # 文件上传
    UPLOAD_DIR: str = "./uploads"
    MAX_FILE_SIZE: int = 20 * 1024 * 1024  # 20MB
    ALLOWED_EXTENSIONS: str = ".txt,.md,.markdown,.pdf,.docx,.xlsx"
    # 分块
    CHUNK_SIZE: int = 512
    CHUNK_OVERLAP: int = 64
    # Reranker (bge-reranker-base 本地加载，true 启用)
    RERANKER_ENABLED: bool = False
    # 检索
    RRF_K: int = 60
    EMBEDDING_TIMEOUT: int = 10
    RETRIEVAL_TOP_K: int = 5
    RETRIEVAL_THRESHOLD: float = 0.3
    RETRIEVAL_RERANK_TOP_K: int = 3
    # Langfuse 可观测性 (留空则不启用)
    LANGFUSE_PUBLIC_KEY: str = ""
    LANGFUSE_SECRET_KEY: str = ""
    LANGFUSE_HOST: str = "https://cloud.langfuse.com"

    class Config:
        env_file = ".env"

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]


settings = Settings()

# 英文停用词
EN_STOP = frozenset(
    {
        "the",
        "a",
        "an",
        "is",
        "are",
        "was",
        "were",
        "be",
        "been",
        "being",
        "have",
        "has",
        "had",
        "do",
        "does",
        "did",
        "will",
        "would",
        "could",
        "should",
        "may",
        "might",
        "can",
        "shall",
        "to",
        "of",
        "in",
        "for",
        "on",
        "with",
        "at",
        "by",
        "from",
        "as",
        "into",
        "about",
        "what",
        "which",
        "who",
        "when",
        "where",
        "how",
        "that",
        "this",
        "it",
        "and",
        "or",
        "but",
        "not",
        "no",
        "if",
        "so",
        "than",
        "too",
        "very",
        "please",
        "tell",
        "know",
        "want",
        "need",
    }
)

# 中文停用词
ZH_STOP = frozenset(
    {
        "的",
        "了",
        "吗",
        "呢",
        "吧",
        "啊",
        "哦",
        "嗯",
        "是",
        "在",
        "有",
        "和",
        "与",
        "或",
        "但",
        "而",
        "把",
        "被",
        "从",
        "到",
        "对",
        "为",
        "什么",
        "怎么",
        "如何",
        "为什么",
        "哪些",
        "哪个",
        "是不是",
        "可以",
        "能",
        "会",
        "要",
        "想",
        "请",
        "我",
        "你",
        "他",
        "她",
        "它",
        "们",
    }
)

# 启动时若未配置 SECRET_KEY，自动生成并警告
_SECRET_KEY_AUTO = False
if not settings.SECRET_KEY:
    settings.SECRET_KEY = secrets.token_urlsafe(48)
    _SECRET_KEY_AUTO = True
    import logging

    logging.getLogger(__name__).warning(
        "SECRET_KEY 未设置，已使用随机密钥（重启后所有 token 失效）。"
        "生产环境请在 .env 中设置 SECRET_KEY。"
    )
