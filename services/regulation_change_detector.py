from __future__ import annotations

import hashlib
import json
from datetime import datetime
from typing import Any, Dict, Optional, Tuple

from config.dashscope_config import ModelRegistry, get_dashscope_async_client
from models.regulation_change import ChangeReviewStatus, RegulationChangeRecord


class RegulationChangeDetector:
    """
    法规变更检测服务：
    1) 对新旧法规 JSON 进行规范化序列化
    2) 基于 MD5 / SHA256 判断是否发生内容变更
    3) 有变更时调用 qwen-plus 生成变更摘要
    4) 返回待审核记录（pending_review）
    """

    async def detect_change(
        self,
        new_regulation: Dict[str, Any],
        old_regulation: Optional[Dict[str, Any]] = None,
    ) -> RegulationChangeRecord:
        regulation_id = str(
            new_regulation.get("regulation_id")
            or new_regulation.get("id")
            or new_regulation.get("code")
            or "unknown_regulation"
        )
        regulation_title = new_regulation.get("title")

        new_canonical = self._canonical_json(new_regulation)
        new_md5, new_sha256 = self._hash_payload(new_canonical)

        old_md5: Optional[str] = None
        old_sha256: Optional[str] = None
        changed = True

        if old_regulation is not None:
            old_canonical = self._canonical_json(old_regulation)
            old_md5, old_sha256 = self._hash_payload(old_canonical)
            changed = (new_md5 != old_md5) or (new_sha256 != old_sha256)

        summary: Optional[str] = None
        if changed:
            summary = await self._summarize_change(
                new_regulation=new_regulation,
                old_regulation=old_regulation,
            )

        now = datetime.utcnow()
        return RegulationChangeRecord(
            regulation_id=regulation_id,
            regulation_title=regulation_title,
            changed=changed,
            old_md5=old_md5,
            new_md5=new_md5,
            old_sha256=old_sha256,
            new_sha256=new_sha256,
            summary=summary,
            status=ChangeReviewStatus.PENDING_REVIEW,
            new_payload=new_regulation,
            old_payload=old_regulation,
            created_at=now,
            updated_at=now,
        )

    def _canonical_json(self, payload: Dict[str, Any]) -> str:
        # sort_keys + compact separator 保证同内容得到稳定 hash
        return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))

    def _hash_payload(self, canonical_payload: str) -> Tuple[str, str]:
        raw = canonical_payload.encode("utf-8")
        md5_value = hashlib.md5(raw).hexdigest()
        sha256_value = hashlib.sha256(raw).hexdigest()
        return md5_value, sha256_value

    async def _summarize_change(
        self,
        new_regulation: Dict[str, Any],
        old_regulation: Optional[Dict[str, Any]],
    ) -> str:
        client = get_dashscope_async_client()
        system_prompt = (
            "你是法律知识库变更审计助手。"
            "请基于新旧法规 JSON 的对比结果，输出简洁、可审计的中文摘要。"
            "必须包含：主要变化点、潜在影响条款范围、建议审核关注点。"
        )
        user_prompt = (
            "请生成法规变更摘要。\n\n"
            f"旧法规JSON:\n{json.dumps(old_regulation, ensure_ascii=False, indent=2) if old_regulation else '无（首次入库）'}\n\n"
            f"新法规JSON:\n{json.dumps(new_regulation, ensure_ascii=False, indent=2)}"
        )

        completion = await client.chat.completions.create(
            model=ModelRegistry.TEXT_ROUTER,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.1,
        )
        return (completion.choices[0].message.content or "").strip()


__all__ = ["RegulationChangeDetector"]

