from __future__ import annotations

import os
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


__all__ = [
    "get_milvus_client",
]

