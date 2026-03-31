from __future__ import annotations

import os
from functools import lru_cache
from typing import Optional

from elasticsearch import AsyncElasticsearch


ELASTICSEARCH_URL_ENV = "ELASTICSEARCH_URL"
ELASTICSEARCH_USERNAME_ENV = "ELASTICSEARCH_USERNAME"
ELASTICSEARCH_PASSWORD_ENV = "ELASTICSEARCH_PASSWORD"

DEFAULT_ELASTICSEARCH_URL = "http://localhost:9200"


@lru_cache(maxsize=1)
def get_es_client() -> AsyncElasticsearch:
    """
    获取 Elasticsearch Async 客户端单例。

    - 强烈建议在生产环境开启 HTTPS 与鉴权。
    - 具体索引结构与 mapping 后续在领域建模阶段补充。
    """

    url = os.getenv(ELASTICSEARCH_URL_ENV, DEFAULT_ELASTICSEARCH_URL)
    username: Optional[str] = os.getenv(ELASTICSEARCH_USERNAME_ENV)
    password: Optional[str] = os.getenv(ELASTICSEARCH_PASSWORD_ENV)

    if username and password:
        basic_auth = (username, password)
    else:
        basic_auth = None

    return AsyncElasticsearch(
        hosts=[url],
        basic_auth=basic_auth,
    )


__all__ = [
    "get_es_client",
]

