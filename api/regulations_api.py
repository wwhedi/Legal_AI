from __future__ import annotations

import asyncio
from datetime import datetime
import hashlib
import json
import re
from typing import Any, Dict, List, Optional, Sequence, Tuple
from uuid import UUID

from fastapi import APIRouter, Body, Depends, File, HTTPException, Query, UploadFile
from pydantic import BaseModel, Field
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from config.db_elasticsearch import get_es_client
from config.db_milvus import get_milvus_client
from config.db_postgres import RegulationChangeRecord, get_db_session
from parsers.metadata_injector import inject_hierarchical_context
from parsers.legal_parser_enhanced import FineGrainedLegalParser
from services.embedding_service import EmbeddingService
from services.regulation_change_detector import RegulationChangeDetector
from models.chunk_schema import EffectiveStatus


router = APIRouter(prefix="/regulations", tags=["regulations"])


class PendingRegulationChangeItem(BaseModel):
    id: UUID
    regulation_id: str
    regulation_title: Optional[str] = None
    summary: Optional[str] = None
    status: str = Field(..., description="pending_review/approved/rejected")
    created_at: datetime
    updated_at: datetime


class PendingRegulationChangeResponse(BaseModel):
    total: int
    items: List[PendingRegulationChangeItem]


class RegulationUploadRequest(BaseModel):
    """
    JSON 上传模式：
    - 若 `payload` 为法规 JSON：可包含 regulation_id/title/text 等字段；
    - 若仅提供 `text`：系统会先解析 text，再构造结构化 payload 用于变更检测与待审入库。
    """

    payload: Optional[Dict[str, Any]] = Field(default=None, description="法规原始 JSON")
    text: Optional[str] = Field(default=None, description="法规全文（纯文本）")
    law_title: Optional[str] = Field(default=None, description="法规标题（可选）")
    regulation_id: Optional[str] = Field(default=None, description="法规唯一标识（可选）")


class RegulationUploadResponse(BaseModel):
    changed: bool
    status: str
    record_id: Optional[str] = None
    regulation_id: str
    regulation_title: Optional[str] = None
    summary: Optional[str] = None


class RegulationApproveResponse(BaseModel):
    id: str
    regulation_id: str
    status: str
    indexed_chunk_count: int


async def _get_latest_regulation_payload(
    session: AsyncSession, regulation_id: str
) -> Optional[Dict[str, Any]]:
    stmt = (
        select(RegulationChangeRecord)
        .where(RegulationChangeRecord.regulation_id == regulation_id)
        .order_by(desc(RegulationChangeRecord.created_at))
        .limit(1)
    )
    row = (await session.execute(stmt)).scalars().first()
    return row.new_payload if row else None


def _coerce_upload_to_payload(
    *,
    payload: Optional[Dict[str, Any]],
    text: Optional[str],
    law_title: Optional[str],
    regulation_id: Optional[str],
) -> Dict[str, Any]:
    if payload is not None:
        return payload

    if not text or not str(text).strip():
        raise HTTPException(
            status_code=400, detail="Either `payload` or non-empty `text` is required."
        )

    parser = FineGrainedLegalParser()
    parsed = parser.parse(text=text, law_title=law_title)

    rid = regulation_id or parsed.get("law_title") or "unknown_regulation"
    title = law_title or parsed.get("law_title")
    return {
        "regulation_id": rid,
        "title": title,
        "raw_text": text,
        "tree": parsed.get("tree"),
        "clauses": parsed.get("clauses"),
    }


def _normalize_article_number(value: Optional[str]) -> Optional[str]:
    if not value:
        return None
    digits = re.sub(r"\D+", "", str(value))
    return digits or None


def _extract_article_number_from_heading(tiao_heading: Optional[str]) -> Optional[str]:
    if not tiao_heading:
        return None
    # e.g. 第617条
    m = re.search(r"第(\d+)\s*条", str(tiao_heading))
    return m.group(1) if m else None


def _chunk_canonical_id(regulation_id: str, chunk_text: str) -> str:
    """
    为 ES 与 Milvus 生成一致的 canonical_id（按 chunk 维度）。
    规则：regulation_id + sha256(chunk_text) -> 稳定、可复算、可去重。
    """

    digest = hashlib.sha256(chunk_text.encode("utf-8")).hexdigest()[:32]
    return f"{regulation_id}:{digest}"


def _map_sxx_to_effective_status(sxx: Any) -> EffectiveStatus:
    """
    flk 生命周期 sxx -> EffectiveStatus
    - 4: 尚未生效 -> INVALID
    - 3: 有效 -> VALID
    - 2: 已修改 -> REVISED
    - 1: 已废止 -> REPEALED
    """
    try:
        n = int(sxx)
    except Exception:
        return EffectiveStatus.VALID
    if n == 3:
        return EffectiveStatus.VALID
    if n == 2:
        return EffectiveStatus.REVISED
    if n == 1:
        return EffectiveStatus.REPEALED
    return EffectiveStatus.INVALID


def _status_display_label(status: EffectiveStatus) -> str:
    mapping = {
        EffectiveStatus.VALID: "【有效】",
        EffectiveStatus.REVISED: "【已修改】",
        EffectiveStatus.REPEALED: "【已废止】",
        EffectiveStatus.INVALID: "【尚未生效】",
    }
    return mapping.get(status, "【有效】")


def _build_chunks_from_payload(payload: Dict[str, Any]) -> Tuple[str, Optional[str], List[Dict[str, Any]]]:
    """
    将法规 payload 统一归一为可索引的 chunk 列表。

    返回：
    - regulation_id
    - regulation_title
    - chunks: [{canonical_id, text, metadata}]
    """

    regulation_id = str(payload.get("regulation_id") or payload.get("id") or payload.get("code") or "unknown_regulation")
    title = payload.get("title") or payload.get("regulation_title")
    law_title = str(title) if title is not None else None

    # 章节/条文的有效性状态：优先用 sxx；没有则默认当作有效文本（保证演示与现行口径可跑通）
    effective_status = _map_sxx_to_effective_status(payload.get("sxx"))
    status_display = _status_display_label(effective_status)
    status_value = effective_status.value

    clauses = payload.get("clauses")
    chunks: List[Dict[str, Any]] = []

    if isinstance(clauses, list) and clauses:
        for idx, clause in enumerate(clauses):
            if not isinstance(clause, dict):
                continue
            law_name = law_title or clause.get("law") or payload.get("law_title")
            tiao_heading = clause.get("tiao")
            chunk_text = inject_hierarchical_context(
                chunk_text=str(clause.get("text") or ""),
                law_title=str(law_name or "未命名法律"),
                bian=clause.get("bian"),
                zhang=clause.get("zhang"),
                jie=clause.get("jie"),
                tiao=tiao_heading,
                kuan=clause.get("kuan"),
                xiang=clause.get("xiang"),
            )

            canonical_id = _chunk_canonical_id(regulation_id, chunk_text)
            metadata = {
                "regulation_id": regulation_id,
                "law_name": law_name,
                "article_number": _normalize_article_number(
                    clause.get("article_number") or _extract_article_number_from_heading(tiao_heading)
                ),
                "title": law_title,
                "chunk_index": idx,
                # 检索过滤与展示所需状态信息
                "status": status_value,  # EN value: valid/revised/repealed/invalid
                "status_display": status_display,  # CN label: 【有效】/【已修改】/【已废止】/【尚未生效】
                "sxx": payload.get("sxx"),
                "effective_status": status_value,
            }
            # 合并原 clause 层级字段，便于可解释与审计
            for k in ("bian", "zhang", "jie", "tiao", "kuan", "xiang"):
                if clause.get(k):
                    metadata[k] = clause.get(k)

            chunks.append({"canonical_id": canonical_id, "text": chunk_text, "metadata": metadata})
    else:
        raw_text = str(payload.get("raw_text") or payload.get("text") or "").strip()
        if raw_text:
            canonical_id = _chunk_canonical_id(regulation_id, raw_text)
            chunks = [
                {
                    "canonical_id": canonical_id,
                    "text": raw_text,
                    "metadata": {
                        "regulation_id": regulation_id,
                        "law_name": law_title,
                        "title": law_title,
                        "chunk_index": 0,
                        "status": status_value,
                        "status_display": status_display,
                        "sxx": payload.get("sxx"),
                        "effective_status": status_value,
                    },
                }
            ]

    return regulation_id, law_title, chunks


@router.get("/pending", response_model=PendingRegulationChangeResponse)
async def list_pending_regulations(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    session: AsyncSession = Depends(get_db_session),
) -> Any:
    """
    待审核法规列表（数据来源：变更检测记录表）。
    """

    stmt = (
        select(RegulationChangeRecord)
        .where(RegulationChangeRecord.status == "pending_review")
        .order_by(desc(RegulationChangeRecord.created_at))
        .limit(limit)
        .offset(offset)
    )
    rows = (await session.execute(stmt)).scalars().all()

    # 简化 total：避免额外 COUNT 带来的开销；如前端需要精确分页可再加 count 查询
    items = [
        PendingRegulationChangeItem(
            id=r.id,
            regulation_id=r.regulation_id,
            regulation_title=r.regulation_title,
            summary=r.summary,
            status=r.status,
            created_at=r.created_at,  # type: ignore[arg-type]
            updated_at=r.updated_at,  # type: ignore[arg-type]
        )
        for r in rows
    ]
    return PendingRegulationChangeResponse(total=len(items), items=items)


@router.post("/upload", response_model=RegulationUploadResponse)
async def upload_regulation(
    req: RegulationUploadRequest = Body(default=RegulationUploadRequest()),
    file: UploadFile | None = File(default=None),
    session: AsyncSession = Depends(get_db_session),
) -> RegulationUploadResponse:
    """
    法规上传入库入口（Pending 队列）：
    - 支持 multipart 上传文件（.json 或纯文本）；
    - 支持 JSON body 直接提交 payload 或 text；
    - 解析 + 变更检测 + 有变更则写入 Postgres（pending_review）。
    """

    file_payload: Optional[Dict[str, Any]] = None
    file_text: Optional[str] = None
    if file is not None:
        raw = await file.read()
        content = (raw or b"").decode("utf-8", errors="ignore").strip()
        if not content:
            raise HTTPException(status_code=400, detail="Uploaded file is empty.")
        is_json = (
            (file.filename or "").lower().endswith(".json")
            or content.startswith("{")
            or content.startswith("[")
        )
        if is_json:
            try:
                file_payload = json.loads(content)
            except Exception as e:
                raise HTTPException(status_code=400, detail=f"Invalid JSON file: {e}") from e
        else:
            file_text = content

    merged_payload = file_payload if file_payload is not None else req.payload
    merged_text = file_text if file_text is not None else req.text

    new_payload = _coerce_upload_to_payload(
        payload=merged_payload,
        text=merged_text,
        law_title=req.law_title,
        regulation_id=req.regulation_id,
    )

    rid = str(
        new_payload.get("regulation_id")
        or new_payload.get("id")
        or new_payload.get("code")
        or req.regulation_id
        or "unknown_regulation"
    )
    old_payload = await _get_latest_regulation_payload(session, rid)

    detector = RegulationChangeDetector()
    record = await detector.detect_change(
        new_regulation=new_payload,
        old_regulation=old_payload,
        session=session,
    )

    return RegulationUploadResponse(
        changed=bool(record.changed),
        status=str(record.status.value if hasattr(record.status, "value") else record.status),
        record_id=str(record.id) if getattr(record, "id", None) else None,
        regulation_id=record.regulation_id,
        regulation_title=record.regulation_title,
        summary=record.summary,
    )


async def _write_es_documents(docs: Sequence[Dict[str, Any]]) -> None:
    """
    将 chunk 文档写入 ES regulations 索引，使用 canonical_id 作为 _id。
    """

    es = get_es_client()
    tasks = []
    for doc in docs:
        doc_id = str(doc["canonical_id"])
        body = {
            "text": doc.get("text", ""),
            "title": doc.get("metadata", {}).get("title"),
            "metadata": doc.get("metadata", {}) or {},
        }
        tasks.append(es.index(index="regulations", id=doc_id, document=body))
    if tasks:
        await asyncio.gather(*tasks)


async def _write_milvus_vectors(
    rows: Sequence[Dict[str, Any]], vectors: Sequence[List[float]]
) -> None:
    """
    将 chunk 向量写入 Milvus regulation_chunks 集合，使用 canonical_id 作为 id。
    说明：集合 schema 需与你的 Milvus 侧定义一致（id/text/metadata/dense_vector）。
    """

    milvus = get_milvus_client()

    payload_rows: List[Dict[str, Any]] = []
    for row, vec in zip(rows, vectors, strict=False):
        payload_rows.append(
            {
                "id": str(row["canonical_id"]),
                "text": row.get("text", ""),
                "metadata": row.get("metadata", {}) or {},
                "dense_vector": vec,
            }
        )

    if not payload_rows:
        return

    def _upsert_sync() -> None:
        # MilvusClient 接口在不同版本中可能是 upsert 或 insert；尽量兼容
        if hasattr(milvus, "upsert"):
            milvus.upsert(collection_name="regulation_chunks", data=payload_rows)
        else:
            milvus.insert(collection_name="regulation_chunks", data=payload_rows)

    await asyncio.to_thread(_upsert_sync)


@router.post("/{id}/approve", response_model=RegulationApproveResponse)
async def approve_regulation_change(
    id: UUID,
    session: AsyncSession = Depends(get_db_session),
) -> RegulationApproveResponse:
    """
    批准入库桥接（The Bridge）：
    1) Postgres: 将 pending_review 记录置为 approved
    2) Embedding: 批量向量化（DashScope text-embedding-v4）
    3) 并发写入：
       - ES: regulations 索引（_id=canonical_id）
       - Milvus: regulation_chunks 集合（id=canonical_id）
    """

    row = await session.get(RegulationChangeRecord, id)
    if not row:
        raise HTTPException(status_code=404, detail="Regulation change record not found.")

    if str(row.status) == "approved":
        return RegulationApproveResponse(
            id=str(row.id),
            regulation_id=row.regulation_id,
            status="approved",
            indexed_chunk_count=0,
        )

    if str(row.status) != "pending_review":
        raise HTTPException(
            status_code=409,
            detail=f"Cannot approve record in status={row.status!s}.",
        )

    payload = row.new_payload or {}
    regulation_id, regulation_title, chunks = _build_chunks_from_payload(payload)
    if not chunks:
        raise HTTPException(status_code=400, detail="No indexable chunks found in payload.")

    texts = [c["text"] for c in chunks]
    embedding_service = EmbeddingService()
    vectors = await embedding_service.embed_texts(
        texts, instruction="为法律条文建立语义索引"
    )
    if len(vectors) != len(texts):
        raise HTTPException(
            status_code=500,
            detail="Embedding service returned unexpected vector count.",
        )

    await asyncio.gather(
        _write_es_documents(chunks),
        _write_milvus_vectors(chunks, vectors),
    )

    row.status = "approved"
    await session.commit()

    return RegulationApproveResponse(
        id=str(row.id),
        regulation_id=regulation_id,
        status="approved",
        indexed_chunk_count=len(chunks),
    )


__all__ = ["router"]

