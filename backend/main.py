from __future__ import annotations

from typing import Literal, Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from services import CitationVerifier, ContractReviewWorkflow, InMemoryStore, RagPipeline


app = FastAPI(title="Legal AI Agent MVP", version="0.1.0")

store = InMemoryStore()
rag = RagPipeline()
verifier = CitationVerifier()
workflow = ContractReviewWorkflow(rag=rag, verifier=verifier, store=store)


class SearchRequest(BaseModel):
    query: str
    top_k: int = 5


class QARequest(BaseModel):
    query: str
    thread_id: Optional[str] = None


class WorkflowRequest(BaseModel):
    contract_text: str = Field(min_length=1)
    query: str = Field(min_length=1)
    approved: bool = False


class ReviewDecision(BaseModel):
    decision: Literal["approve", "correct", "reject", "defer"]
    comment: Optional[str] = None


@app.get("/health")
def health():
    return {"ok": True}


@app.post("/api/search")
def search(req: SearchRequest):
    return rag.search(query=req.query, top_k=req.top_k)


@app.post("/api/qa/ask")
def ask_question(req: QARequest):
    result = rag.search(query=req.query, top_k=5)
    top = result["results"][:2]
    if not top:
        return {
            "answer": "暂未检索到高相关法条，请缩小问题范围后重试。",
            "citations": [],
            "confidence": 0.35,
            "follow_up_suggestions": ["提供合同条款原文", "指出具体法条编号", "指定行业领域"],
        }

    citations = [
        {"law_name": x["metadata"]["law_name"], "article": x["metadata"]["article"]} for x in top
    ]
    checked = verifier.verify(citations, result["results"])
    answer = (
        f"根据《{checked[0]['law_name']}》{checked[0]['article']}，该问题需重点审查违约责任与条款公平性；"
        f"同时参考《{checked[1]['law_name']}》{checked[1]['article']}判断免责条款是否有效。"
    )
    return {
        "answer": answer,
        "citations": checked,
        "confidence": 0.92,
        "follow_up_suggestions": ["是否需要生成修改建议文本？", "是否输出风险分级报告？", "是否展示法条原文？"],
    }


@app.post("/api/workflow/contract-review")
def run_contract_review(req: WorkflowRequest):
    return workflow.run(contract_text=req.contract_text, query=req.query, approved=req.approved)


@app.get("/api/review/pending")
def list_pending():
    pending = [x for x in store.pending_changes if x["review_status"] == "pending_review"]
    return {"total": len(pending), "items": pending}


@app.post("/api/review/{change_id}/decide")
def decide_review(change_id: str, decision: ReviewDecision):
    target = None
    for item in store.pending_changes:
        if item["change_id"] == change_id:
            target = item
            break
    if not target:
        raise HTTPException(status_code=404, detail="change_id not found")

    if decision.decision in ("approve", "correct"):
        target["review_status"] = "approved" if decision.decision == "approve" else "corrected"
        store.append_audit("review_approved", {"change_id": change_id, "comment": decision.comment})
        return {"status": target["review_status"], "indexed": True}
    if decision.decision == "reject":
        target["review_status"] = "rejected"
        store.append_audit("review_rejected", {"change_id": change_id, "comment": decision.comment})
        return {"status": "rejected"}

    target["review_status"] = "deferred"
    store.append_audit("review_deferred", {"change_id": change_id, "comment": decision.comment})
    return {"status": "deferred", "message": "7天后提醒复审（MVP mock）"}


@app.get("/api/audit")
def get_audit():
    return {"total": len(store.audit_logs), "logs": store.audit_logs[-100:]}
