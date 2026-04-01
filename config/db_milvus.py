from __future__ import annotations

import os
import asyncio
from functools import lru_cache
from typing import Optional

from pymilvus import MilvusClient


MILVUS_URI_ENV = "MILVUS_URI"
MILVUS_TOKEN_ENV = "MILVUS_TOKEN"

DEFAULT_MILVUS_URI = "http://localhost:19530"


@lru_cache(maxsize=1)
def get_milvus_client() -> MilvusClient:
    """
    获取 MilvusClient 单例。

    - 后续向量写入/检索逻辑应全部复用该客户端。
    - 连接参数通过环境变量配置，便于在不同环境之间切换。
    """

    uri = os.getenv(MILVUS_URI_ENV, DEFAULT_MILVUS_URI)
    token: Optional[str] = os.getenv(MILVUS_TOKEN_ENV)

    return MilvusClient(
        uri=uri,
        token=token,
    )


async def ensure_milvus_ready() -> None:
    """
    启动时健康检查 + 集合初始化：
    - 连接 Milvus 并做轻量探活（list_collections）
    - 若 regulation_chunks 集合不存在，则创建最小可用集合：
      - 主键：id (string)
      - 向量：dense_vector (float vector)，维度通过环境变量 MILVUS_DENSE_DIM 配置

    注意：当前检索管线还引用 sparse_vector（稀疏召回）。如需生产级稀疏检索，
    请在 Milvus 侧按你的版本能力补齐 SPARSE_FLOAT_VECTOR 字段与索引策略。
    """

    milvus = get_milvus_client()
    collection_name = os.getenv("MILVUS_REGULATION_COLLECTION", "regulation_chunks")
    dense_dim = int(os.getenv("MILVUS_DENSE_DIM", os.getenv("EMBEDDING_DIM", "1024")))

    def _ensure_sync() -> None:
        # 探活
        if hasattr(milvus, "list_collections"):
            existing = set(milvus.list_collections())
        else:
            existing = set()

        if collection_name in existing:
            return

        # 兼容 MilvusClient 的不同版本 create_collection 参数
        if hasattr(milvus, "create_collection"):
            try:
                milvus.create_collection(
                    collection_name=collection_name,
                    dimension=dense_dim,
                    primary_field_name="id",
                    vector_field_name="dense_vector",
                )
                return
            except TypeError:
                # 旧签名兜底
                milvus.create_collection(
                    collection_name=collection_name,
                    dimension=dense_dim,
                )
                return
        raise RuntimeError("MilvusClient does not support create_collection; please upgrade pymilvus.")

    await asyncio.to_thread(_ensure_sync)


__all__ = [
    "get_milvus_client",
    "ensure_milvus_ready",
]

