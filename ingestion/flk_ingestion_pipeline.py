from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from ingestion.flk_async_client import FlkApiClient
from ingestion.docx_extract import docx_bytes_to_text
from ingestion.flk_cleaning import clean_html_content, normalize_text
from parsers.legal_parser_enhanced import FineGrainedLegalParser
from services.regulation_change_detector import RegulationChangeDetector
from config.db_postgres import RegulationChangeRecord


@dataclass
class FlkIngestResult:
    regulation_id: str
    regulation_title: Optional[str]
    changed: bool
    record_id: Optional[str]
    status: str


async def _get_latest_payload_by_regulation_id(
    session: AsyncSession, regulation_id: str
) -> Optional[Dict[str, Any]]:
    from sqlalchemy import desc, select

    stmt = (
        select(RegulationChangeRecord)
        .where(RegulationChangeRecord.regulation_id == regulation_id)
        .order_by(desc(RegulationChangeRecord.created_at))
        .limit(1)
    )
    row = (await session.execute(stmt)).scalars().first()
    return row.new_payload if row else None


def _pick_oss_path(oss_file: Dict[str, Any]) -> Optional[str]:
    # 优先 docx（ossWordPath），否则再试 ofd。
    word_path = oss_file.get("ossWordPath")
    if word_path:
        return word_path
    return oss_file.get("ossWordOfdPath") or oss_file.get("ossPdfPath")


async def ingest_single_flk_document(
    *,
    doc_id: str,
    session: AsyncSession,
    flk_client: Optional[FlkApiClient] = None,
    wb_base_url: Optional[str] = None,
) -> FlkIngestResult:
    """
    闭环中的“入湖”步骤：
    - 从 flk detail 接口获取元数据与正文文件路径
    - 下载 docx 内容 -> 提取文本
    - 用 FineGrainedLegalParser 解析条款 -> 形成 payload
    - RegulationChangeDetector 检测变更 -> 写入 pending_review
    """

    if flk_client is not None:
        client = flk_client
    else:
        client = FlkApiClient(wb_base_url=wb_base_url) if wb_base_url else FlkApiClient()

    detail = await client.fetch_detail(doc_id=doc_id)
    data = (detail or {}).get("data") or {}

    # flk detail 的结构以你提供的样例为准：
    # data.bbbs: 法规唯一 id
    # data.title/flxz/gbrq/sxrq/sxx/ossFile.*
    regulation_id = str(data.get("bbbs") or doc_id)
    regulation_title = data.get("title")

    oss_file = data.get("ossFile") or {}
    oss_path = _pick_oss_path(oss_file)
    if not oss_path:
        raise RuntimeError("flk detail missing ossFile path (ossWordPath/ossWordOfdPath).")

    # 目前我们只实现 docx -> 文本；若 oss_path 来自 ofd/pdf，则会在解析阶段失败。
    file_bytes = await client.download_file(oss_path=oss_path)
    raw_text = docx_bytes_to_text(file_bytes)
    cleaned_text = normalize_text(clean_html_content(raw_text))

    # 解析条款：legal parser 内部用 ^第X条 规则 + 树构建（满足“精细化切片”约束）
    parser = FineGrainedLegalParser()
    parsed = parser.parse(text=cleaned_text, law_title=str(regulation_title or "未命名法律"))

    new_payload: Dict[str, Any] = {
        "regulation_id": regulation_id,
        "title": regulation_title,
        "raw_text": cleaned_text,
        "tree": parsed.get("tree"),
        "clauses": parsed.get("clauses"),
        # 关键：写入 sxx 用于后续检索过滤与旁注展示
        "sxx": data.get("sxx"),
        "flxz": data.get("flxz"),
        "gbrq": data.get("gbrq"),
        "sxrq": data.get("sxrq"),
        "xfFlag": data.get("xfFlag"),
    }

    old_payload = await _get_latest_payload_by_regulation_id(
        session, regulation_id=regulation_id
    )

    detector = RegulationChangeDetector()
    record = await detector.detect_change(
        new_regulation=new_payload,
        old_regulation=old_payload,
        session=session,
    )

    return FlkIngestResult(
        regulation_id=record.regulation_id,
        regulation_title=record.regulation_title,
        changed=bool(record.changed),
        record_id=str(record.id) if getattr(record, "id", None) else None,
        status=str(record.status.value if hasattr(record.status, "value") else record.status),
    )


__all__ = ["ingest_single_flk_document", "FlkIngestResult"]

