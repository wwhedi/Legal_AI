from __future__ import annotations

import asyncio
import uuid
from typing import Any, Dict, Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from agents.contract_review_graph import contract_review_graph


router = APIRouter(prefix="/review", tags=["contract-review"])


class ReviewSubmitRequest(BaseModel):
    contract_id: str | None = None
    contract_text: str = Field(..., min_length=1)
    user_goal: str = "审查合同风险并给出修订建议"


class ReviewApproveRequest(BaseModel):
    approved: bool
    comment: str | None = None
    action: Literal["approve", "revise"] | None = None


async def _run_stream(initial_input: Dict[str, Any] | None, thread_id: str) -> list[Dict[str, Any]]:
    config = {"configurable": {"thread_id": thread_id}}

    def _collect() -> list[Dict[str, Any]]:
        return list(contract_review_graph.stream(initial_input, config=config))

    return await asyncio.to_thread(_collect)


@router.post("/submit")
async def submit_review(req: ReviewSubmitRequest) -> Dict[str, Any]:
    thread_id = f"review_{uuid.uuid4().hex[:12]}"
    initial_state = {
        "contract_id": req.contract_id or thread_id,
        "contract_text": req.contract_text,
        "user_goal": req.user_goal,
    }

    events = await _run_stream(initial_state, thread_id=thread_id)
    state_snapshot = await asyncio.to_thread(
        contract_review_graph.get_state, {"configurable": {"thread_id": thread_id}}
    )
    state_values = getattr(state_snapshot, "values", {}) or {}
    waiting_human = bool(state_values.get("has_high_risk", False)) and not bool(
        state_values.get("report")
    )

    return {
        "thread_id": thread_id,
        "status": "waiting_human_review" if waiting_human else "completed",
        "event_count": len(events),
        "risk_assessment": state_values.get("risk_assessment", {}),
        "interrupt_payload": state_values.get("human_decision"),
    }


@router.post("/approve/{thread_id}")
async def approve_review(thread_id: str, req: ReviewApproveRequest) -> Dict[str, Any]:
    config = {"configurable": {"thread_id": thread_id}}
    state_snapshot = await asyncio.to_thread(contract_review_graph.get_state, config)
    if not getattr(state_snapshot, "values", None):
        raise HTTPException(status_code=404, detail="thread_id not found")

    human_decision = {
        "approved": req.approved,
        "comment": req.comment,
        "action": req.action or ("approve" if req.approved else "revise"),
    }

    await asyncio.to_thread(
        contract_review_graph.update_state,
        config,
        {"human_decision": human_decision},
    )

    # 从 interrupt 点恢复执行
    events = await _run_stream(None, thread_id=thread_id)
    latest_state = await asyncio.to_thread(contract_review_graph.get_state, config)
    values = getattr(latest_state, "values", {}) or {}

    return {
        "thread_id": thread_id,
        "status": "completed" if values.get("report") else "in_progress",
        "event_count": len(events),
        "report": values.get("report"),
        "risk_assessment": values.get("risk_assessment", {}),
    }


@router.get("/stat")
async def review_stat() -> Dict[str, Any]:
    # 轻量占位统计：真实统计可接 PostgreSQL 审核表
    return {
        "service": "contract-review",
        "graph_checkpointer": "enabled",
        "note": "当前为基础统计接口，后续可接入持久化审计指标。",
    }

