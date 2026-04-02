from __future__ import annotations

import asyncio
from typing import Any, Dict, List

from config.db_elasticsearch import get_es_client
from config.db_milvus import get_milvus_client
from services.embedding_service import EmbeddingService
from services.reranker_service import RerankerService


class RetrievalPipeline:
    """
    三路并发检索骨架：
    1) ES BM25
    2) Milvus Dense
    3) Milvus Sparse
    4) RRF 融合 (k=60)
    5) Reranker 精排
    """

    def __init__(self) -> None:
        self.embedding_service = EmbeddingService()
        self.reranker_service = RerankerService()

    async def retrieve(self, query: str, top_k: int = 20) -> List[Dict[str, Any]]:
        query_vector = await self.embedding_service.embed_query(query)

        es_task = asyncio.create_task(self._search_es_bm25(query, top_k=top_k * 3))
        dense_task = asyncio.create_task(
            self._search_milvus_dense(query_vector, top_k=top_k * 3)
        )
        sparse_task = asyncio.create_task(self._search_milvus_sparse(query, top_k=top_k * 3))

        # 方案二：Sparse 不可用时允许降级
        es_results, dense_results, sparse_results = await asyncio.gather(
            es_task, dense_task, sparse_task, return_exceptions=True
        )
        if isinstance(es_results, Exception):
            es_results = []
        if isinstance(dense_results, Exception):
            dense_results = []
        if isinstance(sparse_results, Exception):
            sparse_results = []

        # 默认只开放 VALID + REVISED；当用户显式询问历史/变迁/废止前时开放 REPEALED
        allowed_statuses = {"valid", "revised"}
        if self._query_requests_history(query):
            allowed_statuses.add("repealed")

        es_results = self._filter_by_effective_status(es_results, allowed_statuses)
        dense_results = self._filter_by_effective_status(dense_results, allowed_statuses)
        sparse_results = self._filter_by_effective_status(sparse_results, allowed_statuses)

        fused = self._rrf_fuse(
            ranked_lists=[es_results, dense_results, sparse_results],
            k=60,
        )
        reranked = await self.reranker_service.rerank(query=query, candidates=fused, top_n=top_k)
        return reranked

    async def _search_es_bm25(self, query: str, top_k: int) -> List[Dict[str, Any]]:
        es = get_es_client()
        # 伪代码骨架：实际 index 名称与字段可在接入时调整
        resp = await es.search(
            index="regulations",
            body={
                "size": top_k,
                "query": {
                    "multi_match": {
                        "query": query,
                        "fields": ["text^3", "title^2", "metadata.*"],
                    }
                },
            },
        )
        hits = resp.get("hits", {}).get("hits", [])
        return [
            {
                "id": item.get("_id"),
                "text": item.get("_source", {}).get("text", ""),
                "metadata": item.get("_source", {}).get("metadata", {}),
                "source": "es_bm25",
                "score": float(item.get("_score", 0.0)),
            }
            for item in hits
        ]

    async def _search_milvus_dense(
        self, query_vector: List[float], top_k: int
    ) -> List[Dict[str, Any]]:
        milvus = get_milvus_client()
        # pymilvus MilvusClient 目前为同步接口，使用 to_thread 避免阻塞事件循环
        results = await asyncio.to_thread(
            milvus.search,
            collection_name="regulation_chunks",
            data=[query_vector],
            anns_field="dense_vector",
            limit=top_k,
            output_fields=["text", "metadata"],
        )
        # Milvus 常返回二维：每个 query 对应一个结果列表
        rows = results[0] if results else []
        return [
            {
                "id": str(item.get("id")),
                "text": item.get("entity", {}).get("text", ""),
                "metadata": item.get("entity", {}).get("metadata", {}),
                "source": "milvus_dense",
                "score": float(item.get("distance", 0.0)),
            }
            for item in rows
        ]

    async def _search_milvus_sparse(self, query: str, top_k: int) -> List[Dict[str, Any]]:
        milvus = get_milvus_client()
        # 伪代码骨架：Sparse 检索通常依赖预计算稀疏向量或 BM25 内核字段
        sparse_query_payload = {"text": query}
        results = await asyncio.to_thread(
            milvus.search,
            collection_name="regulation_chunks",
            data=[sparse_query_payload],
            anns_field="sparse_vector",
            limit=top_k,
            output_fields=["text", "metadata"],
        )
        rows = results[0] if results else []
        return [
            {
                "id": str(item.get("id")),
                "text": item.get("entity", {}).get("text", ""),
                "metadata": item.get("entity", {}).get("metadata", {}),
                "source": "milvus_sparse",
                "score": float(item.get("distance", 0.0)),
            }
            for item in rows
        ]

    def _rrf_fuse(self, ranked_lists: List[List[Dict[str, Any]]], k: int = 60) -> List[Dict[str, Any]]:
        """
        Reciprocal Rank Fusion:
        rrf_score(doc) = Σ 1 / (k + rank_i)
        """

        merged: Dict[str, Dict[str, Any]] = {}
        for one_list in ranked_lists:
            for rank, item in enumerate(one_list, start=1):
                doc_id = str(item.get("id"))
                if doc_id not in merged:
                    merged[doc_id] = {
                        **item,
                        "rrf_score": 0.0,
                        "recall_sources": set(),
                    }
                merged[doc_id]["rrf_score"] += 1.0 / (k + rank)
                merged[doc_id]["recall_sources"].add(item.get("source"))

        fused = list(merged.values())
        for item in fused:
            item["recall_sources"] = sorted(item["recall_sources"])

        fused.sort(key=lambda x: x["rrf_score"], reverse=True)
        return fused

    def _query_requests_history(self, query: str) -> bool:
        q = (query or "").lower()
        # 允许用户显式询问历史变迁/废止前
        keywords = ("历史", "变迁", "变更", "废止前", "修改前", "曾经", "repealed", "repeal")
        return any(kw.lower() in q for kw in keywords)

    def _filter_by_effective_status(
        self, items: List[Dict[str, Any]], allowed_statuses: set[str]
    ) -> List[Dict[str, Any]]:
        filtered: List[Dict[str, Any]] = []
        for it in items:
            meta = it.get("metadata") or {}
            status = meta.get("status")
            # 兼容：若 metadata 缺失状态，则保留以避免返回 0（生产中应尽量保证写入一致性）
            if status is None:
                filtered.append(it)
                continue
            if str(status).lower() in allowed_statuses:
                filtered.append(it)
        return filtered


__all__ = ["RetrievalPipeline"]

