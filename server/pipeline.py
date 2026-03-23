from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

from pymongo import ReturnDocument
from pymongo.errors import PyMongoError

from server.db.mongo import books_col, chapters_col, facts_col, mcqs_col
from server.extraction.fact_extractor import run_fact_extraction
from server.extraction.fact_scorer import run_fact_scoring
from server.generation.mcq_pipeline import run_mcq_generation
from server.ingestion.fetch_book import fetch_book_text, split_into_chapters, store_book
from server.processing.coreference import run_coreference_for_book
from server.processing.nlp_pipeline import run_nlp_pipeline
from server.processing.segmenter import segment_chapter
from server.utils.errors import (
    BadInputError,
    BookNotFoundError,
    EmptyResultError,
    PipelineInProgressError,
)

logger = logging.getLogger(__name__)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _validate_book_id(book_id: int) -> None:
    if not isinstance(book_id, int) or book_id <= 0:
        raise BadInputError("book_id must be a positive integer.")


def _has_enough_mcqs(book_id: int, min_existing: int) -> bool:
    return mcqs_col.count_documents({"book_id": book_id}) >= int(min_existing)


def _acquire_pipeline_lock(book_id: int, ttl_seconds: int) -> dict | None:
    now = _utcnow()
    stale_before = now - timedelta(seconds=int(ttl_seconds))

    # Lock is represented by books.status == "processing". If the lock is stale, it can be taken over.
    #
    # Important: do NOT use `upsert=True` with a filter that can intentionally fail (when another worker holds
    # the lock). Otherwise MongoDB will attempt to insert a new document with the same `_id` and raise
    # DuplicateKeyError instead of returning `None`.
    books_col.update_one(
        {"_id": book_id},
        {"$setOnInsert": {"title": "Unknown Title", "created_at": now}, "$set": {"updated_at": now}},
        upsert=True,
    )

    return books_col.find_one_and_update(
        {
            "_id": book_id,
            "$or": [
                {"status": {"$ne": "processing"}},
                {"processing_started_at": {"$lt": stale_before}},
                {"processing_started_at": {"$exists": False}},
            ],
        },
        {
            "$set": {
                "status": "processing",
                "processing_started_at": now,
                "last_error": None,
                "updated_at": now,
            }
        },
        return_document=ReturnDocument.AFTER,
    )


def run_pipeline(
    book_id: int,
    mcq_target: int = 100,
    *,
    min_existing: int = 10,
    lock_ttl_seconds: int = 60 * 60,
) -> int:
    """
    End-to-end deterministic pipeline for one Gutenberg `book_id`.
    Returns number of MCQs stored (up to `mcq_target`).
    """
    _validate_book_id(book_id)

    if _has_enough_mcqs(book_id, min_existing):
        logger.info("Skipping pipeline for book_id=%s (MCQs already exist).", book_id)
        return mcqs_col.count_documents({"book_id": book_id})

    try:
        lock_doc = _acquire_pipeline_lock(book_id, ttl_seconds=lock_ttl_seconds)
    except PyMongoError as e:
        raise RuntimeError("MongoDB error while acquiring pipeline lock.") from e

    if lock_doc is None:
        raise PipelineInProgressError(
            f"Pipeline already running for book_id={book_id}. Please retry shortly."
        )

    try:
        # Re-check after lock acquisition (another worker may have finished meanwhile).
        if _has_enough_mcqs(book_id, min_existing):
            books_col.update_one(
                {"_id": book_id},
                {"$set": {"status": "completed", "updated_at": _utcnow()}},
            )
            return mcqs_col.count_documents({"book_id": book_id})

        logger.info("Fetching Gutenberg text for book_id=%s", book_id)
        try:
            text = fetch_book_text(book_id)
        except BookNotFoundError:
            raise
        except Exception as e:
            raise RuntimeError(f"Network failure fetching Gutenberg for id {book_id}.") from e

        chapters = split_into_chapters(text)
        if not chapters:
            raise EmptyResultError("Book text could not be split into chapters.")

        store_book(book_id, "Unknown Title", chapters)

        for chapter in chapters_col.find({"book_id": book_id}).sort("chapter_number", 1):
            segment_chapter(chapter)
        logger.info("Segmentation done for book_id=%s", book_id)

        run_coreference_for_book(book_id)
        run_nlp_pipeline(book_id)
        run_fact_extraction(book_id)
        run_fact_scoring(book_id)

        n = run_mcq_generation(book_id, target=mcq_target)
        if n <= 0:
            raise EmptyResultError("MCQ generation returned 0 items.")

        fact_count = facts_col.count_documents({"book_id": book_id})
        logger.info(
            "Pipeline complete for book_id=%s: facts=%s mcqs=%s",
            book_id,
            fact_count,
            n,
        )

        books_col.update_one(
            {"_id": book_id},
            {"$set": {"status": "completed", "updated_at": _utcnow(), "mcq_count": n}},
        )
        return n
    except Exception as e:
        books_col.update_one(
            {"_id": book_id},
            {"$set": {"status": "error", "last_error": str(e), "updated_at": _utcnow()}},
        )
        raise
