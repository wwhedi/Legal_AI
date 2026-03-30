# Legal AI Agent MVP (from plan v3)

This is a runnable MVP implementation aligned to the plan's core flows:

- Regulation retrieval (`/api/search`)
- Legal QA (`/api/qa/ask`)
- Contract review workflow with human interrupt (`/api/workflow/contract-review`)
- Regulation review pending/decision (`/api/review/*`)
- Audit trail (`/api/audit`)

## Run

```bash
cd backend
python -m pip install -r requirements.txt
python -m uvicorn main:app --reload --port 8000
```

## Quick test

```bash
curl -X POST http://127.0.0.1:8000/api/workflow/contract-review ^
  -H "Content-Type: application/json" ^
  -d "{\"contract_text\":\"乙方违约需支付50%违约金。甲方免责。\",\"query\":\"违约金与免责条款效力\"}"
```

Then call again with `"approved": true` to continue from interrupt to completed report.

## Notes

- Current version uses in-memory mock data and deterministic scoring.
- Replace `services.py` adapters with real DashScope / Milvus / Elasticsearch / Neo4j connectors for production.
