from typing import AsyncGenerator

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
        kwargs = dict(model=self.model, messages=messages, temperature=0.3, stream=True)
        if self.api_key:
            kwargs["api_key"] = self.api_key
        if self.api_base:
            kwargs["api_base"] = self.api_base
        response = await litellm.acompletion(**kwargs)
        async for chunk in response:
            delta = chunk.choices[0].delta.get("content")
            if delta:
                yield delta

    async def complete(self, messages: list[dict]) -> str:
        kwargs = dict(model=self.model, messages=messages, temperature=0.3)
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

    async def embed(self, texts: list[str]) -> list[list[float]]:
        import httpx

        try:
            if self.api_base:
                url = f"{self.api_base.rstrip('/')}/embeddings"
                async with httpx.AsyncClient(timeout=30) as client:
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
