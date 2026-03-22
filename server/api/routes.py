from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, HTTPException, Path, Query
from pymongo.errors import PyMongoError

from server.api.models import GenerateBody, GenerateResponse, McqOut
from server.config import get_settings
from server.db.mongo import mcqs_col
from server.pipeline import run_pipeline
from server.utils.errors import (
    BadInputError,
    BookNotFoundError,
    EmptyResultError,
    PipelineInProgressError,
)

logger = logging.getLogger(__name__)

router = APIRouter()


def _serialize_mcq(doc: dict[str, Any]) -> McqOut:
    return McqOut(
        question=doc.get("question") or "",
        options=list(doc.get("options") or []),
        correct_answer=doc.get("correct_answer") or "",
        difficulty=doc.get("difficulty"),
        quality=float(doc.get("quality")) if doc.get("quality") is not None else None,
    )


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/mcqs/{book_id}", response_model=GenerateResponse)
def get_mcqs(
    book_id: int = Path(..., gt=0),
    limit: int | None = Query(None, gt=0, le=100),
) -> GenerateResponse:
    settings = get_settings()
    lim = limit or settings.mcq_return_limit
    try:
        docs = list(
            mcqs_col.find({"book_id": book_id}).sort("quality", -1).limit(lim)
        )
        return GenerateResponse(mcqs=[_serialize_mcq(d) for d in docs])
    except PyMongoError as e:
        logger.exception("Mongo error in GET /mcqs/%s", book_id)
        raise HTTPException(status_code=500, detail="Database error.") from e


@router.post("/generate", response_model=GenerateResponse)
def generate(body: GenerateBody) -> GenerateResponse:
    settings = get_settings()
    book_id = body.book_id
    lim = settings.mcq_return_limit

    try:
        existing = mcqs_col.count_documents({"book_id": book_id})
        if existing < lim:
            run_pipeline(
                book_id,
                mcq_target=settings.mcq_target,
                min_existing=lim,
                lock_ttl_seconds=settings.pipeline_lock_ttl_seconds,
            )

        docs = list(
            mcqs_col.find({"book_id": book_id}).sort("quality", -1).limit(lim)
        )
        if not docs:
            raise EmptyResultError("No MCQs found for this book.")

        return GenerateResponse(mcqs=[_serialize_mcq(d) for d in docs])
    except BadInputError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except BookNotFoundError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except PipelineInProgressError as e:
        raise HTTPException(status_code=500, detail=str(e)) from e
    except EmptyResultError as e:
        raise HTTPException(status_code=500, detail=str(e)) from e
    except PyMongoError as e:
        logger.exception("Mongo error in POST /generate")
        raise HTTPException(status_code=500, detail="Database error.") from e
    except Exception as e:
        logger.exception("Unhandled error in POST /generate")
        raise HTTPException(status_code=500, detail=f"Server error: {e!s}") from e

