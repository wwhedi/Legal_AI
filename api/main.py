from __future__ import annotations

from fastapi import FastAPI

from api.qa_api import router as qa_router
from api.review_api import router as review_router


app = FastAPI(title="Legal Contract Review API", version="0.1.0")
app.include_router(review_router)
app.include_router(qa_router)

