from __future__ import annotations

from fastapi import FastAPI

from api.regulations_api import router as regulations_router
from api.review_api import router as review_router
from config.db_postgres import init_postgres_models


app = FastAPI(title="Legal Contract Review API", version="0.1.0")
app.include_router(review_router)
app.include_router(regulations_router)


@app.on_event("startup")
async def _startup() -> None:
    await init_postgres_models()

