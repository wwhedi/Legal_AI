from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class ChangeReviewStatus(str, Enum):
    PENDING_REVIEW = "pending_review"
    APPROVED = "approved"
    REJECTED = "rejected"


class RegulationChangeRecord(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    regulation_id: str = Field(..., description="法规唯一标识")
    regulation_title: Optional[str] = Field(default=None, description="法规标题")

    changed: bool = Field(..., description="是否检测到内容变更")
    old_md5: Optional[str] = Field(default=None)
    new_md5: str = Field(...)
    old_sha256: Optional[str] = Field(default=None)
    new_sha256: str = Field(...)

    summary: Optional[str] = Field(default=None, description="由 qwen-plus 生成的变更摘要")
    status: ChangeReviewStatus = Field(default=ChangeReviewStatus.PENDING_REVIEW)

    new_payload: Dict[str, Any] = Field(
        ..., description="新法规原始 JSON，用于后续审核追溯"
    )
    old_payload: Optional[Dict[str, Any]] = Field(
        default=None, description="旧法规 JSON（如存在）"
    )

    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


__all__ = ["ChangeReviewStatus", "RegulationChangeRecord"]

