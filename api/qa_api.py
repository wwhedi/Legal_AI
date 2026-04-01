from __future__ import annotations

import asyncio
from typing import Any, Dict, List, Optional

from fastapi import APIRouter
from pydantic import BaseModel, Field

from agents.legal_qa_agent import legal_qa_graph


router = APIRouter(prefix="/qa", tags=["legal-qa"])


class AskQARequest(BaseModel):
    question: str = Field(..., min_length=1)
    user_context: Dict[str, Any] = Field(default_factory=dict)


class AskQAResponse(BaseModel):
    question: str
    intent: Optional[str] = None
    intent_reason: Optional[str] = None
    answer: str
    citations: List[Dict[str, Any]] = Field(default_factory=list)
    verification_details: List[Dict[str, Any]] = Field(default_factory=list)
    answer_needs_human_review: bool = False


@router.post("/ask", response_model=AskQAResponse)
async def ask_legal_qa(req: AskQARequest) -> AskQAResponse:
    initial_state: Dict[str, Any] = {
        "question": req.question,
        "user_context": req.user_context,
    }
    result = await asyncio.to_thread(legal_qa_graph.invoke, initial_state)
    state = result or {}

    return AskQAResponse(
        question=req.question,
        intent=state.get("intent"),
        intent_reason=state.get("intent_reason"),
        answer=state.get("answer") or "未生成回答，请稍后重试。",
        citations=state.get("citations") or [],
        verification_details=state.get("verification_details") or [],
        answer_needs_human_review=bool(state.get("answer_needs_human_review", False)),
    )


__all__ = ["router"]
