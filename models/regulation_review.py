from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from .chunk_schema import ChangeType, EffectiveStatus, LawLevel


class ReviewStatus(str, Enum):
    """
    审核流程状态
    """

    PENDING = "pending"  # 待审核
    APPROVED = "approved"  # 已通过
    REJECTED = "rejected"  # 已驳回
    NEEDS_CLARIFICATION = "needs_clarification"  # 需要补充说明


class ReviewSource(str, Enum):
    """
    审核任务来源
    """

    MANUAL = "manual"  # 人工创建
    AUTO_IMPORT = "auto_import"  # 批量导入触发
    MODEL_SUGGESTION = "model_suggestion"  # 大模型建议的修改


class RegulationReviewTask(BaseModel):
    """
    法规变更审核任务模型
    """

    id: UUID = Field(default_factory=uuid4)

    chunk_id: UUID = Field(..., description="待审核的法规 Chunk ID")
    regulation_id: str = Field(..., description="所属法规 ID，冗余字段便于检索")

    law_level: LawLevel = Field(..., description="法规层级（冗余字段便于过滤）")
    effective_status: EffectiveStatus = Field(
        ..., description="法规当前的生效状态（由系统计算或人工指定）"
    )
    proposed_change_type: ChangeType = Field(
        ..., description="建议对该 Chunk 进行的变更类型"
    )

    # 审核元信息
    source: ReviewSource = Field(
        default=ReviewSource.MANUAL,
        description="审核任务来源",
    )
    created_by: Optional[str] = Field(
        default=None, description="任务创建人（操作账号或系统标识）"
    )

    reviewer_id: Optional[str] = Field(
        default=None,
        description="分配的审核人（如律师/合规专员账号 ID）",
    )
    reviewer_name: Optional[str] = Field(
        default=None,
        description="审核人姓名或展示名称（便于审计日志查看）",
    )

    status: ReviewStatus = Field(
        default=ReviewStatus.PENDING,
        description="审核状态",
    )
    review_comment: Optional[str] = Field(
        default=None,
        description="审核意见正文，要求可追溯、可解释",
    )
    model_explanation: Optional[str] = Field(
        default=None,
        description="如由大模型发起/辅助的修改，这里保留模型给出的解释，辅助减轻幻觉风险",
    )

    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="任务创建时间（UTC）",
    )
    updated_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="任务最近一次更新时间（UTC）",
    )
    reviewed_at: Optional[datetime] = Field(
        default=None,
        description="实际完成审核的时间（UTC）",
    )

    class Config:
        # 对外暴露时可以方便地序列化为 JSON
        use_enum_values = True


__all__ = [
    "ReviewStatus",
    "ReviewSource",
    "RegulationReviewTask",
]

