from typing import AsyncGenerator

import httpx
import litellm

from app.config import settings


class LLMService:
    def __init__(self):
        self.model = settings.LLM_MODEL
        self.api_key = settings.LLM_API_KEY
        self.api_base = settings.LLM_BASE_URL or None
        # 自定义base_url时，加openai/前缀让litellm走兼容接口
        if self.api_base and not self.model.startswith("openai/"):
            self.model = f"openai/{self.model}"

    async def stream_chat(self, messages: list[dict]) -> AsyncGenerator[str, None]:
        kwargs = dict(model=self.model, messages=messages, temperature=0.0, stream=True, timeout=30)
        if self.api_key:
            kwargs["api_key"] = self.api_key
        if self.api_base:
            kwargs["api_base"] = self.api_base
        response = await litellm.acompletion(**kwargs)
        async for chunk in response:
            delta = chunk.choices[0].delta.get("content")
            if delta:
                yield delta

    async def complete(self, messages: list[dict], **overrides) -> str:
        kwargs = dict(model=self.model, messages=messages, temperature=0.0, timeout=30)
        kwargs.update(overrides)
        if self.api_key:
            kwargs["api_key"] = self.api_key
        if self.api_base:
            kwargs["api_base"] = self.api_base
        response = await litellm.acompletion(**kwargs)
        return response.choices[0].message.content


class EmbeddingService:
    def __init__(self):
        self.model = settings.EMBEDDING_MODEL
        self.api_key = settings.EMBEDDING_API_KEY or settings.LLM_API_KEY
        self.api_base = settings.EMBEDDING_BASE_URL or settings.LLM_BASE_URL or None
        self._client: httpx.AsyncClient | None = None

    def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(timeout=30)
        return self._client

    async def embed(self, texts: list[str]) -> list[list[float]]:
        try:
            if self.api_base:
                url = f"{self.api_base.rstrip('/')}/embeddings"
                client = self._get_client()
                resp = await client.post(
                    url,
                    json={"model": self.model, "input": texts},
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json",
                    },
                )
                resp.raise_for_status()
                data = resp.json()
            else:
                # fallback to litellm for default provider
                import litellm

                kwargs = dict(model=self.model, input=texts)
                if self.api_key:
                    kwargs["api_key"] = self.api_key
                resp = await litellm.aembedding(**kwargs)
                data = resp.model_dump()
            return [item["embedding"] for item in data["data"]]
        except Exception as e:
            import logging

            logging.getLogger(__name__).warning(
                f"Embedding 服务不可用: {e}\n"
                "向量搜索降级为 BM25 全文检索。请检查 EMBEDDING_MODEL 配置。"
            )
            raise

    async def embed_single(self, text: str) -> list[float]:
        result = await self.embed([text])
        return result[0]


llm_service = LLMService()
embedding_service = EmbeddingService()
