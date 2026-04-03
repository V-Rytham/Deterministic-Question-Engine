from __future__ import annotations

import logging
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from typing import Any

from fastapi import APIRouter, HTTPException, Path, Query
from fastapi.responses import JSONResponse
from pymongo.errors import PyMongoError

from server.api.models import BookSearchResult, GenerateBody, GenerateResponse, McqOut
from server.config import get_settings
from server.db.mongo import books_index_col, mcqs_col
from server.ingestion.books_index import (
    ensure_books_index_indexes,
    fetch_and_cache_external,
    search_books_index,
)
from server.pipeline import run_pipeline
from server.utils.errors import (
    BadInputError,
    BookNotFoundError,
    EmptyResultError,
    PipelineInProgressError,
)

logger = logging.getLogger(__name__)

router = APIRouter()

_executor = ThreadPoolExecutor(max_workers=1)
_inflight_lock = threading.Lock()
_inflight: set[int] = set()

_BOOK_SEARCH_CACHE_TTL_SECONDS = 600
_book_search_cache: dict[str, tuple[float, list[BookSearchResult]]] = {}


def _serialize_mcq(doc: dict[str, Any]) -> McqOut:
    return McqOut(
        question=doc.get("question") or "",
        options=list(doc.get("options") or []),
        correct_answer=doc.get("correct_answer") or "",
        difficulty=doc.get("difficulty"),
        quality=float(doc.get("quality")) if doc.get("quality") is not None else None,
    )


def _to_search_result(doc: dict[str, Any]) -> BookSearchResult:
    return BookSearchResult(
        id=int(doc.get("book_id")),
        title=str(doc.get("title") or "Untitled"),
        author=str(doc.get("author") or "Unknown Author"),
    )


@router.get("/books/search", response_model=list[BookSearchResult])
def search_books(
    q: str = Query(..., min_length=2, max_length=120),
    limit: int = Query(8, ge=1, le=10),
) -> list[BookSearchResult]:
    query = q.strip()
    cache_key = f"{query.lower()}:{limit}"
    now = time.time()
    cached = _book_search_cache.get(cache_key)

    if cached and now - cached[0] < _BOOK_SEARCH_CACHE_TTL_SECONDS:
        return cached[1]

    try:
        ensure_books_index_indexes(books_index_col)

        local_results = search_books_index(books_index_col, query=query, limit=limit)
        if local_results:
            out = [_to_search_result(doc) for doc in local_results]
            _book_search_cache[cache_key] = (now, out)
            return out

        external_results = fetch_and_cache_external(books_index_col, query=query, limit=limit)
        out = [_to_search_result(doc) for doc in external_results]
        _book_search_cache[cache_key] = (now, out)
        return out
    except PyMongoError as e:
        logger.exception("Mongo error during local book search query=%s", query)
        raise HTTPException(status_code=500, detail="Database error.") from e
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e)) from e


@router.get("/health")
def health() -> dict[str, str]:
    settings = get_settings()
    return {"status": "ok" if settings.mongo_uri else "degraded"}


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
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e)) from e


@router.post("/generate", response_model=GenerateResponse)
def generate(body: GenerateBody) -> GenerateResponse:
    settings = get_settings()
    book_id = body.book_id
    workers = body.workers
    lim = settings.mcq_return_limit

    try:
        existing = mcqs_col.count_documents({"book_id": book_id})
        if existing >= lim:
            docs = list(
                mcqs_col.find({"book_id": book_id}).sort("quality", -1).limit(lim)
            )
            return GenerateResponse(mcqs=[_serialize_mcq(d) for d in docs])

        # Avoid blocking requests (Render can gateway-timeout long pipelines).
        # Kick off pipeline in the background and let clients poll /mcqs or /status.
        with _inflight_lock:
            already = book_id in _inflight
            if not already:
                _inflight.add(book_id)

                def _run() -> None:
                    try:
                        run_pipeline(
                            book_id,
                            mcq_target=settings.mcq_target,
                            min_existing=lim,
                            lock_ttl_seconds=settings.pipeline_lock_ttl_seconds,
                            workers=workers,
                        )
                    except Exception:
                        logger.exception("Background pipeline failed for book_id=%s", book_id)
                    finally:
                        with _inflight_lock:
                            _inflight.discard(book_id)

                _executor.submit(_run)

        return JSONResponse(
            status_code=202,
            headers={"Retry-After": "10"},
            content={
                "status": "processing",
                "book_id": book_id,
                "message": "Pipeline started. Poll /mcqs/{book_id} or /status/{book_id}.",
            },
        )
    except BadInputError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except BookNotFoundError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except PipelineInProgressError as e:
        return JSONResponse(
            status_code=202,
            headers={"Retry-After": "10"},
            content={"status": "processing", "book_id": book_id, "message": str(e)},
        )
    except EmptyResultError as e:
        raise HTTPException(status_code=500, detail=str(e)) from e
    except PyMongoError as e:
        logger.exception("Mongo error in POST /generate")
        raise HTTPException(status_code=500, detail="Database error.") from e
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e)) from e
    except Exception as e:
        logger.exception("Unhandled error in POST /generate")
        raise HTTPException(status_code=500, detail=f"Server error: {e!s}") from e


@router.get("/status/{book_id}")
def status(book_id: int = Path(..., gt=0)) -> dict[str, Any]:
    """
    Lightweight status endpoint for long-running pipeline runs.
    """
    try:
        from server.db.mongo import books_col, facts_col

        book = books_col.find_one(
            {"_id": book_id},
            {"status": 1, "mcq_count": 1, "processing_started_at": 1, "last_error": 1},
        )
        return {
            "book_id": book_id,
            "book": book or None,
            "facts": facts_col.count_documents({"book_id": book_id}),
            "mcqs": mcqs_col.count_documents({"book_id": book_id}),
        }
    except PyMongoError as e:
        logger.exception("Mongo error in GET /status/%s", book_id)
        raise HTTPException(status_code=500, detail="Database error.") from e
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e)) from e
