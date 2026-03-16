from __future__ import annotations

from fastapi import FastAPI

from question_service.app.api.routes import router
from question_service.app.db.mongo import ensure_indexes

app = FastAPI(title="Question Generation Service")


@app.on_event("startup")
def startup() -> None:
    ensure_indexes()


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


app.include_router(router)
