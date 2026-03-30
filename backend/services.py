from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from mock_data import MOCK_CHANGE_RECORDS, MOCK_REGULATIONS


@dataclass
class SearchResult:
    content: str
    metadata: dict[str, Any]
    raw_score: float
    adjusted_score: float


class InMemoryStore:
    def __init__(self) -> None:
        self.pending_changes = [dict(x) for x in MOCK_CHANGE_RECORDS]
        self.audit_logs: list[dict[str, Any]] = []

    def append_audit(self, action: str, detail: dict[str, Any]) -> None:
        self.audit_logs.append(
            {
                "timestamp": datetime.now().isoformat(timespec="seconds"),
                "action": action,
                "detail": detail,
            }
        )


class RagPipeline:
    """Mock 三路检索 + RRF + rerank."""

    def search(self, query: str, top_k: int = 5) -> dict[str, Any]:
        q = query.lower()
        es = []
        milvus = []
        neo4j = []

        for row in MOCK_REGULATIONS:
            score = 0.0
            joined = f"{row['law_name']} {row['article']} {row['content']} {' '.join(row['keywords'])}".lower()
            for token in ["违约金", "免责", "格式条款", "无人机", "审批", "数据"]:
                if token in q and token in joined:
                    score += 1.0
            if score <= 0:
                continue
            es.append((row, score + 0.2))
            milvus.append((row, score + 0.4))
            neo4j.append((row, score + 0.1))

        # naive RRF-like fusion for demo
        merged: dict[str, float] = {}
        sources = [es, milvus, neo4j]
        for source in sources:
            source.sort(key=lambda x: x[1], reverse=True)
            for rank, (row, _) in enumerate(source, start=1):
                merged[row["law_id"]] = merged.get(row["law_id"], 0.0) + 1 / (60 + rank)

        results = []
        for row in MOCK_REGULATIONS:
            if row["law_id"] in merged:
                raw = merged[row["law_id"]]
                level_bonus = {"法律": 0.95, "司法解释": 0.8, "行政法规": 0.85}.get(
                    row["law_level"], 0.7
                )
                adjusted = raw * (0.8 + 0.2 * level_bonus)
                results.append(
                    SearchResult(
                        content=row["content"],
                        metadata={
                            "law_id": row["law_id"],
                            "law_name": row["law_name"],
                            "article": row["article"],
                            "status": row["status"],
                            "law_level": row["law_level"],
                        },
                        raw_score=round(raw, 4),
                        adjusted_score=round(adjusted, 4),
                    )
                )

        results.sort(key=lambda x: x.adjusted_score, reverse=True)
        return {
            "query": query,
            "retrieval_trace": {
                "es_count": len(es),
                "milvus_count": len(milvus),
                "neo4j_count": len(neo4j),
            },
            "results": [r.__dict__ for r in results[:top_k]],
        }


class CitationVerifier:
    def verify(self, citations: list[dict[str, str]], search_results: list[dict[str, Any]]) -> list[dict[str, Any]]:
        index = {
            f"{r['metadata'].get('law_name','')}_{r['metadata'].get('article','')}": r for r in search_results
        }
        checked = []
        for c in citations:
            key = f"{c.get('law_name','')}_{c.get('article','')}"
            if key in index:
                checked.append(
                    {
                        **c,
                        "verified": True,
                        "source_status": index[key]["metadata"].get("status", "未知"),
                        "warning": None,
                    }
                )
            else:
                checked.append(
                    {
                        **c,
                        "verified": False,
                        "source_status": "未知",
                        "warning": "未在知识库命中，需人工复核",
                    }
                )
        return checked


class ContractReviewWorkflow:
    """Mock LangGraph: plan -> extract -> search -> assess -> human_gate -> report."""

    def __init__(self, rag: RagPipeline, verifier: CitationVerifier, store: InMemoryStore):
        self.rag = rag
        self.verifier = verifier
        self.store = store

    def run(self, contract_text: str, query: str, approved: bool = False) -> dict[str, Any]:
        self.store.append_audit("plan_generated", {"query": query})
        clauses = self._extract_clauses(contract_text)
        self.store.append_audit("clauses_extracted", {"count": len(clauses)})

        retrieval = self.rag.search(query=query, top_k=5)
        self.store.append_audit("regulation_searched", retrieval["retrieval_trace"])

        risks = self._assess_risks(clauses)
        high_count = len([x for x in risks if x["risk_level"] == "高风险"])
        human_review_required = high_count > 0

        if human_review_required and not approved:
            self.store.append_audit("human_review_interrupt", {"high_risk_count": high_count})
            return {
                "status": "awaiting_human_approval",
                "message": f"发现 {high_count} 项高风险条款，请审核。",
                "graph_step": "human_review",
                "risks": risks,
                "search_results": retrieval["results"],
            }

        citations = [
            {"law_name": "民法典", "article": "第585条第2款"},
            {"law_name": "民法典", "article": "第497条"},
        ]
        citation_check = self.verifier.verify(citations, retrieval["results"])
        self.store.append_audit("citations_verified", {"verified": sum(1 for c in citation_check if c["verified"])})

        report = {
            "overall_rating": "中风险-修改后可签署" if high_count <= 1 else "高风险-建议暂缓签署",
            "statistics": {
                "high_risk_count": len([x for x in risks if x["risk_level"] == "高风险"]),
                "medium_risk_count": len([x for x in risks if x["risk_level"] == "中风险"]),
                "low_risk_count": len([x for x in risks if x["risk_level"] == "低风险"]),
            },
            "risk_details": risks,
            "citations": citation_check,
            "disclaimer": "本报告由 AI 辅助生成，仅供参考，不构成法律意见。",
        }
        self.store.append_audit("report_generated", {"overall_rating": report["overall_rating"]})
        return {
            "status": "completed",
            "graph_step": "report",
            "search_results": retrieval["results"],
            "report": report,
        }

    def _extract_clauses(self, contract_text: str) -> list[dict[str, str]]:
        parts = [p.strip() for p in contract_text.replace("\n", "。").split("。") if p.strip()]
        return [{"clause_id": f"C{i+1}", "clause_text": p} for i, p in enumerate(parts[:12])]

    def _assess_risks(self, clauses: list[dict[str, str]]) -> list[dict[str, Any]]:
        results = []
        for c in clauses:
            text = c["clause_text"]
            if "50%" in text or "免责" in text or "单方解除" in text:
                lvl = "高风险"
                desc = "违约责任或免责分配明显失衡，存在无效风险。"
                legal_basis = ["民法典第585条第2款", "民法典第497条"]
                suggestion = "建议调整违约金比例并删除绝对免责表述。"
            elif "争议" in text or "管辖" in text:
                lvl = "中风险"
                desc = "争议解决机制不完整，执行成本较高。"
                legal_basis = ["民法典合同编通则"]
                suggestion = "补充管辖法院/仲裁地与送达条款。"
            else:
                lvl = "低风险"
                desc = "条款总体可接受。"
                legal_basis = []
                suggestion = "保持现有文本。"

            results.append(
                {
                    "clause_id": c["clause_id"],
                    "clause_text": text,
                    "risk_level": lvl,
                    "risk_description": desc,
                    "legal_basis": legal_basis,
                    "suggestion": suggestion,
                    "confidence": 0.93 if lvl == "高风险" else 0.82,
                }
            )
        return results
