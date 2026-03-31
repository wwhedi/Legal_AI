from __future__ import annotations

from datetime import datetime
from typing import Any, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from config.db_postgres import RegulationChangeRecord, get_db_session


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


__all__ = ["router"]

