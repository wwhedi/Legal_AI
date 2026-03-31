from __future__ import annotations

import os
from datetime import date, datetime
from typing import Any, Dict, List, Optional

import httpx

from config.dashscope_config import ModelRegistry


class RerankerService:
    """
    gte-rerank 封装，并在原始分数上施加法律业务后处理权重。
    """

    def __init__(self) -> None:
        self._base_url = os.getenv("DASHSCOPE_BASE_URL", "https://dashscope.aliyuncs.com")
        self._api_key = os.getenv("DASHSCOPE_API_KEY", "")
        self._timeout = float(os.getenv("DASHSCOPE_TIMEOUT_SECONDS", "30"))

    async def rerank(
        self, query: str, candidates: List[Dict[str, Any]], top_n: int = 20
    ) -> List[Dict[str, Any]]:
        if not candidates:
            return []

        raw_scores = await self._call_dashscope_rerank(query=query, candidates=candidates)
        rescored = self._apply_legal_weights(candidates=candidates, raw_scores=raw_scores)
        rescored.sort(key=lambda item: item["final_score"], reverse=True)
        return rescored[:top_n]

    async def _call_dashscope_rerank(
        self, query: str, candidates: List[Dict[str, Any]]
    ) -> List[float]:
        """
        调用 DashScope gte-rerank。默认使用可配置 endpoint：
        - 环境变量 `DASHSCOPE_RERANK_ENDPOINT` 优先
        - 默认 `/api/v1/services/rerank/text-rerank/text-rerank`
        """

        endpoint = os.getenv(
            "DASHSCOPE_RERANK_ENDPOINT",
            "/api/v1/services/rerank/text-rerank/text-rerank",
        )
        url = f"{self._base_url.rstrip('/')}/{endpoint.lstrip('/')}"
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": ModelRegistry.RERANKER,
            "input": {
                "query": query,
                "documents": [str(item.get("text", "")) for item in candidates],
            },
            "parameters": {"top_n": len(candidates)},
        }

        async with httpx.AsyncClient(timeout=self._timeout) as client:
            response = await client.post(url, headers=headers, json=payload)
            response.raise_for_status()
            body = response.json()

        # 常见结构：output.results=[{index, score}]
        results = body.get("output", {}).get("results", [])
        scores = [0.0] * len(candidates)
        for item in results:
            idx = int(item.get("index", -1))
            if 0 <= idx < len(scores):
                scores[idx] = float(item.get("score", 0.0))
        return scores

    def _apply_legal_weights(
        self, candidates: List[Dict[str, Any]], raw_scores: List[float]
    ) -> List[Dict[str, Any]]:
        """
        在 Reranker 原始分数基础上做法律业务加权：
        1) law_level：宪法权重最高
        2) effective_date：越新权重越高
        3) status：已废止显著扣分
        """

        rescored: List[Dict[str, Any]] = []
        for idx, candidate in enumerate(candidates):
            metadata = candidate.get("metadata", {}) or {}
            base_score = raw_scores[idx] if idx < len(raw_scores) else 0.0

            law_boost = self._law_level_boost(metadata.get("law_level"))
            date_boost = self._effective_date_boost(metadata.get("effective_date"))
            status_penalty = self._status_penalty(metadata.get("status"))

            # 后处理公式：线性可解释，便于审计
            final_score = base_score * law_boost * date_boost + status_penalty
            rescored.append(
                {
                    **candidate,
                    "raw_score": base_score,
                    "final_score": final_score,
                }
            )
        return rescored

    def _law_level_boost(self, law_level: Optional[str]) -> float:
        if not law_level:
            return 1.0
        normalized = str(law_level).lower()
        mapping = {
            "constitution": 1.25,
            "law": 1.12,
            "administrative_regulation": 1.06,
            "judicial_interpretation": 1.04,
            "local_regulation": 1.00,
            "normative_document": 0.96,
        }
        return mapping.get(normalized, 1.0)

    def _effective_date_boost(self, effective_date: Optional[str]) -> float:
        if not effective_date:
            return 1.0
        parsed = self._parse_date(effective_date)
        if not parsed:
            return 1.0

        days = (date.today() - parsed).days
        if days <= 365:
            return 1.08
        if days <= 3 * 365:
            return 1.04
        if days <= 10 * 365:
            return 1.00
        return 0.95

    def _status_penalty(self, status: Optional[str]) -> float:
        if not status:
            return 0.0
        normalized = str(status).lower()
        if normalized in {"repealed", "invalid", "abolished"}:
            return -0.20
        if normalized in {"revised"}:
            return -0.05
        return 0.0

    def _parse_date(self, value: str) -> Optional[date]:
        for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%Y.%m.%d"):
            try:
                return datetime.strptime(value, fmt).date()
            except ValueError:
                continue
        return None


__all__ = ["RerankerService"]

