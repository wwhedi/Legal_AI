from __future__ import annotations

from typing import List, Sequence

from config.dashscope_config import ModelRegistry, get_dashscope_async_client


class EmbeddingService:
    """
    DashScope text-embedding-v4 异步封装。

    instruction 用于区分查询向量与文档向量场景，示例：
    - 查询：instruction="为法律问题检索最相关条文"
    - 文档：instruction="为法律条文建立语义索引"
    """

    async def embed_texts(
        self, texts: Sequence[str], instruction: str | None = None
    ) -> List[List[float]]:
        if not texts:
            return []

        payload_input = []
        for text in texts:
            if instruction:
                payload_input.append(f"{instruction}\n{text}")
            else:
                payload_input.append(text)

        client = get_dashscope_async_client()
        response = await client.embeddings.create(
            model=ModelRegistry.EMBEDDING,
            input=payload_input,
        )
        # OpenAI 兼容格式：response.data[i].embedding
        return [item.embedding for item in response.data]

    async def embed_query(self, query: str) -> List[float]:
        vectors = await self.embed_texts(
            [query], instruction="为法律问题检索最相关条文"
        )
        return vectors[0] if vectors else []

    async def embed_document(self, document_text: str) -> List[float]:
        vectors = await self.embed_texts(
            [document_text], instruction="为法律条文建立语义索引"
        )
        return vectors[0] if vectors else []


__all__ = ["EmbeddingService"]

