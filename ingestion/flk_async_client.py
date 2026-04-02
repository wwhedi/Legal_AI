from __future__ import annotations

import asyncio
import random
from typing import Any, Dict, Optional

import httpx


FLK_API_BASE_URL = "https://flk.npc.gov.cn/api"
FLK_WB_DEFAULT_BASE_URL = "https://wb.flk.npc.gov.cn"


class FlkApiClient:
    """
    flk.npc.gov.cn 异步客户端：
    - 列表/详情获取（JSON）
    - 依据详情里的 ossFile path 下载 docx/ofd 文件
    """

    def __init__(
        self,
        *,
        wb_base_url: str = FLK_WB_DEFAULT_BASE_URL,
        timeout_seconds: float = 60.0,
        max_concurrency: int = 2,
        max_retries: int = 5,
    ) -> None:
        self._wb_base_url = wb_base_url.rstrip("/")
        self._timeout_seconds = timeout_seconds
        self._sem = asyncio.Semaphore(max_concurrency)
        self._max_retries = max_retries

    async def fetch_detail(self, *, doc_id: str) -> Dict[str, Any]:
        """
        详情接口：通常为 POST { id: doc_id }
        返回结构按 flk 的 result.data / result.msg / result.code。
        """
        url = f"{FLK_API_BASE_URL}/detail"
        payload = {"id": doc_id}

        async with httpx.AsyncClient(timeout=self._timeout_seconds) as client:
            resp = await self._request_with_retry(client, "POST", url, json=payload)
            return resp

    async def download_file(self, *, oss_path: str) -> bytes:
        """
        下载 ossWordPath / ossWordOfdPath 等。
        """
        if not oss_path:
            raise ValueError("oss_path is empty.")
        url = f"{self._wb_base_url}/{oss_path.lstrip('/')}"

        async with httpx.AsyncClient(timeout=self._timeout_seconds) as client:
            for attempt in range(self._max_retries):
                try:
                    async with self._sem:
                        r = await client.get(url)
                    if r.status_code in {429} or r.status_code >= 500:
                        raise httpx.HTTPStatusError(
                            f"HTTP {r.status_code} for {url}",
                            request=r.request,
                            response=r,
                        )
                    r.raise_for_status()
                    return r.content
                except Exception:
                    if attempt >= self._max_retries - 1:
                        raise
                    await asyncio.sleep((2**attempt) + random.random())

        raise RuntimeError("Failed to download file after retries.")

    async def _request_with_retry(
        self,
        client: httpx.AsyncClient,
        method: str,
        url: str,
        *,
        json: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        async with self._sem:
            for attempt in range(self._max_retries):
                try:
                    if method.upper() == "POST":
                        r = await client.post(url, json=json)
                    else:
                        r = await client.get(url)
                    if r.status_code in {429} or r.status_code >= 500:
                        raise httpx.HTTPStatusError(
                            f"HTTP {r.status_code} for {url}",
                            request=r.request,
                            response=r,
                        )
                    r.raise_for_status()
                    return r.json()
                except Exception:
                    if attempt >= self._max_retries - 1:
                        raise
                    await asyncio.sleep((2**attempt) + random.random())

        raise RuntimeError("Unreachable.")


__all__ = ["FlkApiClient"]

