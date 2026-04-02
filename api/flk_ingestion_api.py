from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from config.db_postgres import get_db_session
from ingestion.flk_ingestion_pipeline import FlkIngestResult, ingest_single_flk_document


router = APIRouter(prefix="/ingestions/flk", tags=["flk-ingestion"])


class FlkIngestRequest(BaseModel):
    """
    单文档入湖请求：
    - doc_id：flk detail 接口的 id 参数（例如你给的 detail?id=... 中的 id）
    """

    doc_id: str = Field(..., min_length=1)
    # 可选：用于下载正文时替换 wb.flk 基础域名
    wb_base_url: Optional[str] = Field(
        default=None,
        description="可选：正文下载的 base URL（若默认域名不可用）。",
    )


class FlkIngestResponse(BaseModel):
    regulation_id: str
    regulation_title: Optional[str]
    changed: bool
    record_id: Optional[str]
    status: str


@router.post("/ingest", response_model=FlkIngestResponse)
async def ingest(req: FlkIngestRequest, session: AsyncSession = Depends(get_db_session)) -> FlkIngestResponse:
    result: FlkIngestResult = await ingest_single_flk_document(
        doc_id=req.doc_id,
        session=session,
        wb_base_url=req.wb_base_url,
    )

    return FlkIngestResponse(
        regulation_id=result.regulation_id,
        regulation_title=result.regulation_title,
        changed=result.changed,
        record_id=result.record_id,
        status=result.status,
    )


__all__ = ["router"]

