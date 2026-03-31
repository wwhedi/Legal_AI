from __future__ import annotations

import asyncio
from typing import Any, Dict, List, Literal, TypedDict

from langgraph.graph import END, START, StateGraph

from config.dashscope_config import ModelRegistry, get_dashscope_async_client
from rag.retrieval_pipeline import RetrievalPipeline


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
        citations.append(
            {
                "ref_id": f"[{i}]",
                "doc_id": doc.get("id"),
                "law_name": meta.get("law_name"),
                "article": meta.get("article_number"),
                "status": meta.get("status"),
                "score": doc.get("final_score", doc.get("rrf_score", 0.0)),
            }
        )
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

    try:
        client = get_dashscope_async_client()
        completion = await client.chat.completions.create(
            model=ModelRegistry.TEXT_ROUTER,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.1,
        )
        answer = (completion.choices[0].message.content or "").strip()
    except Exception:
        # 降级输出，确保流程可用
        answer = (
            "根据已检索法规片段，初步结论如下：\n"
            "- 请优先核对引用条款的现行有效性与适用范围。\n"
            "- 当前回答为检索增强的草案，建议由法务复核。"
        )

    return {"answer": answer, "citations": citations}


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

