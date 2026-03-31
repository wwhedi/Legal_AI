from __future__ import annotations

import os
from functools import lru_cache
from typing import Dict

from openai import AsyncOpenAI

# 阿里云 DashScope OpenAI 兼容模式基础配置
_DASHSCOPE_BASE_URL = os.getenv(
    "DASHSCOPE_BASE_URL",
    "https://dashscope.aliyuncs.com/compatible-mode/v1",
)
_DASHSCOPE_API_KEY_ENV = "DASHSCOPE_API_KEY"


class ModelRegistry:
    """
    统一管理项目中使用到的大模型标识，避免在代码中散落硬编码字符串。
    """

    CORE_REASONING = "qwen3-max"
    TEXT_ROUTER = "qwen-plus"
    EMBEDDING = "text-embedding-v4"
    RERANKER = "gte-rerank"

    @classmethod
    def as_dict(cls) -> Dict[str, str]:
        return {
            "core_reasoning": cls.CORE_REASONING,
            "text_router": cls.TEXT_ROUTER,
            "embedding": cls.EMBEDDING,
            "reranker": cls.RERANKER,
        }


@lru_cache(maxsize=1)
def get_dashscope_async_client() -> AsyncOpenAI:
    """
    获取 DashScope OpenAI-Compatible Async 客户端单例。

    - 所有发往大模型的调用都应通过该客户端，以便统一配置与审计。
    - API Key 从环境变量 `DASHSCOPE_API_KEY` 读取。
    """

    api_key = os.getenv(_DASHSCOPE_API_KEY_ENV)
    if not api_key:
        raise RuntimeError(
            f"Environment variable `{_DASHSCOPE_API_KEY_ENV}` is required for DashScope client."
        )

    return AsyncOpenAI(
        api_key=api_key,
        base_url=_DASHSCOPE_BASE_URL,
    )


__all__ = [
    "ModelRegistry",
    "get_dashscope_async_client",
]

