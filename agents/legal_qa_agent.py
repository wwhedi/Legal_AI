from __future__ import annotations

import asyncio
from typing import Any, Dict, List, Literal, TypedDict

from langgraph.graph import END, START, StateGraph

from config.dashscope_config import ModelRegistry, create_chat_completion
from rag.retrieval_pipeline import RetrievalPipeline
from services.citation_verifier import CitationVerifier


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

    retrieved_docs: List[Dict[str, Any]]
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
    intent = state.get("intent", "UNKNOWN")
    pipeline = RetrievalPipeline()

    # 按意图调整召回深度
    top_k_map = {
        "PRECISE_LOOKUP": 12,
        "CONCEPT_EXPLAIN": 10,
        "COMPLIANCE_CHECK": 16,
        "PROCEDURE_GUIDE": 10,
        "UNKNOWN": 8,
    }
    top_k = top_k_map.get(intent, 8)
    docs = await pipeline.retrieve(query=question, top_k=top_k)
    return {"retrieved_docs": docs}


async def generate_answer(state: LegalQAState) -> LegalQAState:
    question = state.get("question", "")
    intent = state.get("intent", "UNKNOWN")
    docs = state.get("retrieved_docs", [])

    context_blocks = []
    citations: List[Dict[str, Any]] = []
    for i, doc in enumerate(docs[:8], start=1):
        meta = doc.get("metadata", {}) or {}
        status_display = meta.get("status_display") or None
        citations.append(
            {
                "ref_id": f"[{i}]",
                "doc_id": doc.get("id"),
                "law_name": meta.get("law_name"),
                "article": meta.get("article_number"),
                "status": meta.get("status"),
                "status_display": status_display,
                "score": doc.get("final_score", doc.get("rrf_score", 0.0)),
            }
        )
        if status_display:
            context_blocks.append(f"[{i}] {status_display}\n{doc.get('text', '')}")
        else:
            context_blocks.append(f"[{i}] {doc.get('text', '')}")

    if not context_blocks:
        return {
            "answer": "未检索到可用法规依据，建议补充问题上下文后重试。",
            "citations": [],
        }

    system_prompt = (
        "你是企业法律问答助手。回答必须基于给定检索证据，不得编造法条。"
        "若证据不足，请明确说明不确定性并提示补充信息。"
    )
    user_prompt = (
        f"问题意图: {intent}\n"
        f"用户问题: {question}\n\n"
        "检索证据:\n"
        + "\n\n".join(context_blocks)
        + "\n\n请输出：\n1) 简明结论\n2) 法律依据（引用[编号]）\n3) 实务建议"
    )

    verifier = CitationVerifier()
    answer_needs_human_review = False
    verification_details: List[Dict[str, Any]] = []
    try:
        answer = await create_chat_completion(
            model=ModelRegistry.text_router(),
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=0.1,
        )

        # 强制引用校验闭环：
        # 1) 先校验首轮回答中的显式引用；
        # 2) 若存在未验证引用，基于检索原文要求模型重写，再次校验。
        verify_results = await verifier.verify_citations(
            llm_answer=answer,
            retrieved_contexts=docs[:8],
        )
        verification_details = verify_results
        unverified = [item for item in verify_results if not item.get("verified", False)]
        if unverified:
            invalid_refs = ", ".join(item.get("raw", "") for item in unverified if item.get("raw")) or "未知引用"
            revise_user_prompt = (
                f"原回答存在未通过校验的引用：{invalid_refs}\n"
                "请仅基于下面证据重新生成回答，不得引用证据外法条。\n\n"
                f"问题意图: {intent}\n"
                f"用户问题: {question}\n\n"
                "检索证据:\n"
                + "\n\n".join(context_blocks)
                + "\n\n请输出：\n1) 简明结论\n2) 法律依据（仅允许引用[编号]）\n3) 实务建议"
            )
            revised_answer = await create_chat_completion(
                model=ModelRegistry.text_router(),
                system_prompt=system_prompt,
                user_prompt=revise_user_prompt,
                temperature=0.0,
            )
            revised_verify = await verifier.verify_citations(
                llm_answer=revised_answer,
                retrieved_contexts=docs[:8],
            )
            answer = revised_answer
            verify_results = revised_verify
            verification_details = revised_verify
            unverified = [item for item in verify_results if not item.get("verified", False)]
            answer_needs_human_review = len(unverified) > 0

        # 将校验结果挂回 citations，前端/调用方可直接观察闭环结果
        verify_map = {item.get("raw"): item for item in verify_results}
        for item in citations:
            ref_id = item.get("ref_id")
            v = verify_map.get(ref_id)
            if v is not None:
                item["verified"] = bool(v.get("verified", False))
                item["verify_source"] = v.get("verify_source")
        if verify_results and not answer_needs_human_review:
            answer_needs_human_review = any(not it.get("verified", False) for it in verify_results)
    except Exception:
        # 降级输出，确保流程可用
        answer = (
            "根据已检索法规片段，初步结论如下：\n"
            "- 请优先核对引用条款的现行有效性与适用范围。\n"
            "- 当前回答为检索增强的草案，建议由法务复核。"
        )
        answer_needs_human_review = True

    return {
        "answer": answer,
        "citations": citations,
        "verification_details": verification_details,
        "answer_needs_human_review": answer_needs_human_review,
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

