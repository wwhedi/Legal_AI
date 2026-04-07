from __future__ import annotations

import asyncio
import logging
from typing import Any, Dict, List, Literal, TypedDict

from langgraph.graph import END, START, StateGraph

from services.farui_service import FaruiLegalService
from services.reasoning_service import ReasoningService


logger = logging.getLogger(__name__)


LegalIntent = Literal[
    "PRECISE_LOOKUP",
    "CONCEPT_EXPLAIN",
    "COMPLIANCE_CHECK",
    "PROCEDURE_GUIDE",
    "UNKNOWN",
]


class LegalQAState(TypedDict, total=False):
    question: str
    user_context: Dict[str, Any]

    intent: LegalIntent
    intent_reason: str

    farui_context: str
    farui_statutes: List[Dict[str, Any]]
    farui_error: str
    answer: str
    citations: List[Dict[str, Any]]
    verification_details: List[Dict[str, Any]]
    answer_needs_human_review: bool


async def classify_intent(state: LegalQAState) -> LegalQAState:
    await asyncio.sleep(0)
    q = (state.get("question") or "").strip()

    # 轻量规则分流，后续可替换为 LLM 分类器
    if any(k in q for k in ("第", "条", "法条", "依据", "哪一条", "具体规定")):
        intent: LegalIntent = "PRECISE_LOOKUP"
        reason = "问题包含法条定位信号词。"
    elif any(k in q for k in ("是什么", "含义", "区别", "概念", "如何理解")):
        intent = "CONCEPT_EXPLAIN"
        reason = "问题偏向概念解释。"
    elif any(k in q for k in ("合规", "是否违法", "风险", "处罚", "责任")):
        intent = "COMPLIANCE_CHECK"
        reason = "问题偏向合规与责任判断。"
    elif any(k in q for k in ("流程", "步骤", "怎么办理", "如何申请", "程序")):
        intent = "PROCEDURE_GUIDE"
        reason = "问题偏向程序性指引。"
    else:
        intent = "UNKNOWN"
        reason = "未命中明确意图特征。"

    return {"intent": intent, "intent_reason": reason}


async def retrieve_knowledge(state: LegalQAState) -> LegalQAState:
    question = state.get("question", "")
    farui_service = FaruiLegalService()

    farui_context = ""
    farui_statutes: List[Dict[str, Any]] = []
    farui_error = ""
    try:
        farui_payload = await farui_service.search_legal_payload(question)
        farui_context = str(farui_payload.get("context") or "")
        farui_statutes = [
            item for item in (farui_payload.get("statutes") or []) if isinstance(item, dict)
        ]
    except Exception as exc:
        farui_error = str(exc)
        logger.exception("Farui API failed.")

    return {
        "farui_context": farui_context,
        "farui_statutes": farui_statutes,
        "farui_error": farui_error,
    }


async def generate_answer(state: LegalQAState) -> LegalQAState:
    question = state.get("question", "")
    intent = state.get("intent", "UNKNOWN")
    farui_context = (state.get("farui_context") or "").strip()
    farui_statutes = state.get("farui_statutes") or []

    if not farui_context:
        return {
            "answer": "未获取到可用法律背景，建议补充问题上下文后重试。",
            "citations": [],
        }

    reasoning = ReasoningService()
    system_prompt = (
        "你是企业法律问答助手。回答必须基于给定法律背景，不得编造法条。"
        "若证据不足，请明确说明不确定性并提示补充信息。"
    )
    user_prompt = (
        f"问题意图: {intent}\n"
        f"用户问题: {question}\n\n"
        "法律背景:\n"
        + farui_context
        + "\n\n请输出：\n1) 简明结论\n2) 法律依据\n3) 实务建议"
    )

    try:
        answer = await reasoning.generate(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
        )
    except Exception:
        answer = (
            "根据法睿提供的法律背景，暂时无法稳定生成最终答复。\n"
            "- 建议稍后重试。\n"
            "- 如用于正式法律意见，请由法务人工复核。"
        )

    citations: List[Dict[str, Any]] = []
    ref_lines: List[str] = []
    for idx, item in enumerate(farui_statutes[:6], start=1):
        law_name = str(item.get("name") or "未标注法规").strip()
        article = str(item.get("article") or "未标注条款").strip()
        quote = str(item.get("quote") or "").strip()
        ref_id = f"[{idx}]"
        citations.append(
            {
                "ref_id": ref_id,
                "law_name": law_name,
                "article": article,
                "status": "valid",
                "status_display": "【法睿检索】",
                "score": 1.0,
                "verified": True,
                "verify_source": "retrieved_context",
            }
        )
        if quote:
            ref_lines.append(f"{ref_id} 《{law_name}》{article}：{quote}")
        else:
            ref_lines.append(f"{ref_id} 《{law_name}》{article}")

    if ref_lines:
        answer += "\n\n法律依据参考：\n" + "\n".join(ref_lines)

    return {
        "answer": answer,
        "citations": citations,
        "verification_details": [],
        "answer_needs_human_review": False,
    }


def build_legal_qa_graph():
    graph = StateGraph(LegalQAState)
    graph.add_node("classify_intent", classify_intent)
    graph.add_node("retrieve_knowledge", retrieve_knowledge)
    graph.add_node("generate_answer", generate_answer)

    graph.add_edge(START, "classify_intent")
    graph.add_edge("classify_intent", "retrieve_knowledge")
    graph.add_edge("retrieve_knowledge", "generate_answer")
    graph.add_edge("generate_answer", END)
    return graph.compile()


legal_qa_graph = build_legal_qa_graph()


__all__ = [
    "LegalQAState",
    "LegalIntent",
    "classify_intent",
    "retrieve_knowledge",
    "generate_answer",
    "build_legal_qa_graph",
    "legal_qa_graph",
]

