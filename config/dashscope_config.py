from __future__ import annotations

import os
from functools import lru_cache
from typing import Dict, List, Optional

from openai import AsyncOpenAI

MODEL_PROVIDER_ENV = "MODEL_PROVIDER"


class LLMProvider:
    DASHSCOPE = "dashscope"
    DEEPSEEK = "deepseek"


def get_model_provider() -> str:
    value = (os.getenv(MODEL_PROVIDER_ENV, LLMProvider.DASHSCOPE) or "").strip().lower()
    if value in {"dashscope", "qwen", "aliyun"}:
        return LLMProvider.DASHSCOPE
    if value in {"deepseek", "ds"}:
        return LLMProvider.DEEPSEEK
    raise RuntimeError(
        f"Unsupported {MODEL_PROVIDER_ENV}={value!r}. Expected 'dashscope' or 'deepseek'."
    )


def _get_provider_base_url(provider: str) -> str:
    if provider == LLMProvider.DASHSCOPE:
        return os.getenv(
            "DASHSCOPE_BASE_URL",
            "https://dashscope.aliyuncs.com/compatible-mode/v1",
        )
    return os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")


def _get_provider_api_key(provider: str) -> str:
    env = "DASHSCOPE_API_KEY" if provider == LLMProvider.DASHSCOPE else "DEEPSEEK_API_KEY"
    api_key = os.getenv(env)
    if not api_key:
        raise RuntimeError(f"Environment variable `{env}` is required for {provider} client.")
    return api_key


class ModelRegistry:
    """
    统一管理项目中使用到的大模型标识，避免在代码中散落硬编码字符串。
    """

    @classmethod
    def core_reasoning(cls) -> str:
        provider = get_model_provider()
        if provider == LLMProvider.DASHSCOPE:
            return os.getenv("DASHSCOPE_CORE_REASONING_MODEL", "qwen3-max")
        # DeepSeek R1 (Reasoner)
        return os.getenv("DEEPSEEK_CORE_REASONING_MODEL", "deepseek-reasoner")

    @classmethod
    def text_router(cls) -> str:
        provider = get_model_provider()
        if provider == LLMProvider.DASHSCOPE:
            return os.getenv("DASHSCOPE_TEXT_ROUTER_MODEL", "qwen-plus")
        # DeepSeek V3 (Chat)
        return os.getenv("DEEPSEEK_TEXT_ROUTER_MODEL", "deepseek-chat")

    @classmethod
    def embedding(cls) -> str:
        provider = get_model_provider()
        if provider == LLMProvider.DASHSCOPE:
            return os.getenv("DASHSCOPE_EMBEDDING_MODEL", "text-embedding-v4")
        # DeepSeek 是否提供 embeddings 取决于你的网关/兼容层；要求显式配置避免误用
        model = (os.getenv("DEEPSEEK_EMBEDDING_MODEL") or "").strip()
        if not model:
            raise RuntimeError(
                "Embedding model is not configured for DeepSeek provider. "
                "Please set `DEEPSEEK_EMBEDDING_MODEL` or switch MODEL_PROVIDER to 'dashscope'."
            )
        return model

    # Rerank 目前仅接入 DashScope HTTP endpoint；保留为常量供 RerankerService 使用
    RERANKER = "gte-rerank"

    @classmethod
    def as_dict(cls) -> Dict[str, str]:
        return {
            "provider": get_model_provider(),
            "core_reasoning": cls.core_reasoning(),
            "text_router": cls.text_router(),
            "embedding": cls.embedding(),
            "reranker": cls.RERANKER,
        }


@lru_cache(maxsize=1)
def get_llm_async_client() -> AsyncOpenAI:
    """
    获取当前 Provider 的 OpenAI-Compatible Async 客户端单例。
    - Provider 通过环境变量 `MODEL_PROVIDER` 切换：dashscope / deepseek
    - API Key 与 base_url 通过各自环境变量配置
    """

    provider = get_model_provider()
    api_key = _get_provider_api_key(provider)
    base_url = _get_provider_base_url(provider)

    return AsyncOpenAI(
        api_key=api_key,
        base_url=base_url,
    )


def _should_strip_system_prompt(provider: str, model: str) -> bool:
    """
    DeepSeek R1 官方建议：不要传 system_prompt。
    这里按模型名做判定（包含 reasoner/r1 即视为 R1 路径）。
    """

    if provider != LLMProvider.DEEPSEEK:
        return False
    m = (model or "").lower()
    return ("reasoner" in m) or (" r1" in m) or m.endswith("r1") or ("-r1" in m)


async def create_chat_completion(
    *,
    model: str,
    system_prompt: Optional[str],
    user_prompt: str,
    temperature: float = 0.1,
) -> str:
    """
    统一的 Chat Completion 调用封装：
    - 根据 Provider/模型自动调整 message 结构（DeepSeek R1 去掉 system_prompt）
    - 返回 assistant content（string）
    """

    provider = get_model_provider()
    client = get_llm_async_client()

    messages: List[Dict[str, str]] = []
    if system_prompt and not _should_strip_system_prompt(provider, model):
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": user_prompt})

    completion = await client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=temperature,
    )
    return (completion.choices[0].message.content or "").strip()


# Backward compatible alias (historical name in this repo)
def get_dashscope_async_client() -> AsyncOpenAI:  # pragma: no cover
    return get_llm_async_client()


__all__ = [
    "LLMProvider",
    "MODEL_PROVIDER_ENV",
    "get_model_provider",
    "ModelRegistry",
    "get_llm_async_client",
    "create_chat_completion",
    "get_dashscope_async_client",
]

