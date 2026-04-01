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


async def ensure_es_ready() -> None:
    """
    启动时健康检查 + 索引初始化：
    - ping ES
    - 若 regulations 索引不存在，则按当前代码使用字段创建最小可用 mapping
    """

    es = get_es_client()
    ok = await es.ping()
    if not ok:
        raise RuntimeError("Elasticsearch ping failed.")

    index_name = os.getenv("ES_REGULATIONS_INDEX", "regulations")
    exists = await es.indices.exists(index=index_name)
    if exists:
        return

    body = {
        "settings": {
            "index": {
                "number_of_shards": int(os.getenv("ES_SHARDS", "1")),
                "number_of_replicas": int(os.getenv("ES_REPLICAS", "0")),
            }
        },
        "mappings": {
            "dynamic": True,
            "properties": {
                "text": {"type": "text"},
                "title": {"type": "text", "fields": {"keyword": {"type": "keyword"}}},
                # metadata.* 在检索中被 multi_match 使用，保持 object + dynamic
                "metadata": {"type": "object", "dynamic": True},
            },
        },
    }
    await es.indices.create(index=index_name, **{"body": body})


__all__ = [
    "get_es_client",
    "ensure_es_ready",
]

