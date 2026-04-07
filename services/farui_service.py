from __future__ import annotations

import asyncio
import json
import logging
import os
from typing import Any, Dict, List

from config.dashscope_config import (
    ModelRegistry,
    create_chat_completion,
    get_farui_temperature,
)


logger = logging.getLogger(__name__)


class FaruiLegalService:
    """
    通义法睿法律背景检索服务：
    - 输入：用户自然语言问题
    - 输出：结构化法律背景字符串（可直接作为下游推理模型 context）
    """

    def __init__(self) -> None:
        self.model_name = ModelRegistry.legal_retriever()
        self.temperature = get_farui_temperature()
        self.timeout_seconds = float(os.getenv("FARUI_TIMEOUT_SECONDS", "20"))

    async def search_legal_context(self, query: str) -> str:
        payload = await self.search_legal_payload(query)
        return payload["context"]

    async def search_legal_payload(self, query: str) -> Dict[str, Any]:
        raw = await asyncio.wait_for(
            self._call_farui(query=query),
            timeout=self.timeout_seconds,
        )
        parsed = self._parse_farui_response(raw)
        return {
            "context": self._format_context(parsed),
            "statutes": parsed.get("statutes") or [],
        }

    async def _call_farui(self, query: str) -> str:
        system_prompt = (
            "你是法律检索与法理分析助手。"
            "请针对用户问题，仅返回 JSON，不要输出多余解释。"
            "JSON schema: "
            "{"
            '"statutes":[{"name":"法规名称","article":"条款编号","quote":"条文或要点"}],'
            '"cases":[{"name":"案例名称","gist":"裁判要点","relevance":"关联理由"}],'
            '"analysis":["初步法理分析要点1","初步法理分析要点2"],'
            '"confidence_note":"对证据充分性与适用边界的提示"'
            "}"
        )
        return await create_chat_completion(
            model=self.model_name,
            system_prompt=system_prompt,
            user_prompt=query,
            temperature=self.temperature,
        )

    def _parse_farui_response(self, raw: str) -> Dict[str, Any]:
        text = (raw or "").strip()
        if not text:
            return {
                "statutes": [],
                "cases": [],
                "analysis": ["法睿未返回可解析内容。"],
                "confidence_note": "证据不足，建议结合本地法规库复核。",
            }
        try:
            data = json.loads(text)
            return {
                "statutes": data.get("statutes") or [],
                "cases": data.get("cases") or [],
                "analysis": data.get("analysis") or [],
                "confidence_note": data.get("confidence_note") or "请结合具体案情进行适用性审查。",
            }
        except Exception:
            logger.warning("Farui response is not valid JSON, fallback to raw text parsing.")
            return {
                "statutes": [],
                "cases": [],
                "analysis": [text],
                "confidence_note": "法睿返回为非结构化文本，已按原文作为初步分析纳入。",
            }

    def _format_context(self, data: Dict[str, Any]) -> str:
        statutes = self._format_statutes(data.get("statutes") or [])
        cases = self._format_cases(data.get("cases") or [])
        analysis = self._format_list(data.get("analysis") or [], default="暂无初步法理分析。")
        confidence_note = str(data.get("confidence_note") or "请结合具体事实与证据补充判断。").strip()

        return (
            "[法睿法律背景]\n"
            "一、法条引用\n"
            f"{statutes}\n\n"
            "二、类案参考\n"
            f"{cases}\n\n"
            "三、初步法理分析\n"
            f"{analysis}\n\n"
            "四、法睿置信提示\n"
            f"- {confidence_note}"
        )

    def _format_statutes(self, statutes: List[Any]) -> str:
        lines: List[str] = []
        for item in statutes:
            if not isinstance(item, dict):
                continue
            name = str(item.get("name") or "未标注法规")
            article = str(item.get("article") or "未标注条款")
            quote = str(item.get("quote") or "").strip()
            if quote:
                lines.append(f"- 《{name}》{article}：{quote}")
            else:
                lines.append(f"- 《{name}》{article}")
        return "\n".join(lines) if lines else "- 暂无法条引用。"

    def _format_cases(self, cases: List[Any]) -> str:
        lines: List[str] = []
        for item in cases:
            if not isinstance(item, dict):
                continue
            name = str(item.get("name") or "未标注案例")
            gist = str(item.get("gist") or "").strip()
            relevance = str(item.get("relevance") or "").strip()
            payload = "；".join(part for part in [gist, relevance] if part)
            lines.append(f"- {name}" + (f"：{payload}" if payload else ""))
        return "\n".join(lines) if lines else "- 暂无类案参考。"

    def _format_list(self, items: List[Any], default: str) -> str:
        lines = [f"- {str(item).strip()}" for item in items if str(item).strip()]
        return "\n".join(lines) if lines else f"- {default}"


__all__ = ["FaruiLegalService"]
