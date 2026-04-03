from __future__ import annotations

import os
import logging
from concurrent.futures import ProcessPoolExecutor
from datetime import datetime, timedelta, timezone
from time import perf_counter

from pymongo import InsertOne, ReturnDocument, UpdateOne
from pymongo.errors import PyMongoError

from server.config import get_settings
from server.db.mongo import books_col, chapters_col, facts_col, mcqs_col, paragraphs_col, sentences_col
from server.extraction.fact_extractor import extract_facts
from server.extraction.fact_scorer import score_fact
from server.generation.deterministic_shuffle import stable_option_order
from server.generation.distractors import _bucket_for_role, build_pools, pick_distractors
from server.generation.question_generation import difficulty_for, generate_question_variants
from server.ingestion.fetch_book import fetch_book_text, split_into_chapters, store_book
from server.processing.coreference import resolve_paragraph_text
from server.processing.nlp_pipeline import process_sentence_batch
from server.processing.segmenter import segment_chapter
from server.processing.spacy_model import get_nlp
from server.utils.deduplication import dedupe_questions
from server.utils.errors import (
    BadInputError,
    BookNotFoundError,
    EmptyResultError,
    PipelineInProgressError,
)
from server.utils.selection import select_top_mcqs

logger = logging.getLogger(__name__)
NLP = None


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _validate_book_id(book_id: int) -> None:
    if not isinstance(book_id, int) or book_id <= 0:
        raise BadInputError("book_id must be a positive integer.")


def init_worker() -> None:
    """
    Warm the spaCy model once per worker process.
    """
    global NLP
    NLP = get_nlp()


def _generate_chapter_mcqs(book_id: int, chapter_id, chapter_number: int, target: int) -> int:
    facts = list(facts_col.find({"book_id": book_id, "chapter_id": chapter_id}).sort("score", -1))
    if not facts:
        return 0

    pools = build_pools(facts)
    candidates: list[dict] = []
    max_facts = min(len(facts), 1200)
    for fact in facts[:max_facts]:
        variants = generate_question_variants(fact)
        for v in variants[:3]:
            correct = (v.get("correct") or "").strip()
            if not correct:
                continue
            role = v.get("answer_role") or "object"
            bucket = _bucket_for_role(fact, role)
            distractors = pick_distractors(correct, bucket, pools, facts, need=3)
            options = stable_option_order([correct] + distractors, f"{fact['_id']}:{v['kind']}")
            candidates.append(
                {
                    "book_id": book_id,
                    "chapter_id": chapter_id,
                    "chapter_number": chapter_number,
                    "question": v["question"],
                    "options": options,
                    "correct_answer": correct,
                    "difficulty": difficulty_for(fact, v["kind"]),
                    "source_fact_id": fact["_id"],
                    "quality": round(float(fact.get("score") or 0.0), 4),
                    "variant_kind": v["kind"],
                }
            )

    if not candidates:
        return 0

    deduped = dedupe_questions(candidates, similarity_threshold=0.88)
    final = select_top_mcqs(deduped, k=target)
    if not final:
        return 0
    mcqs_col.insert_many(final, ordered=True)
    return len(final)


def process_chapter(chapter_doc: dict, mcq_target: int = 100) -> dict[str, int]:
    chapter_id = chapter_doc["_id"]
    chapter_number = int(chapter_doc.get("chapter_number", 0))
    book_id = int(chapter_doc["book_id"])
    logger.info("chapter_start book_id=%s chapter_id=%s", book_id, chapter_id)
    try:
        segment_chapter(chapter_doc)

        para_cursor = paragraphs_col.find({"chapter_id": chapter_id}).sort("order", 1)
        for para in para_cursor:
            sents = list(sentences_col.find({"para_id": para["_id"]}).sort("order", 1))
            if not sents:
                continue
            resolved = resolve_paragraph_text(para["text"])
            if len(resolved) != len(sents):
                updates = [
                    UpdateOne(
                        {"_id": s["_id"]},
                        {"$set": {"resolved_text": s["text"], "coref_applied": False}},
                    )
                    for s in sents
                ]
            else:
                updates = [
                    UpdateOne(
                        {"_id": s["_id"]},
                        {"$set": {"resolved_text": r, "coref_applied": True}},
                    )
                    for s, r in zip(sents, resolved)
                ]
            if updates:
                sentences_col.bulk_write(updates, ordered=True)

        settings = get_settings()
        nlp_batch_size = max(1, int(settings.spacy_batch_size))
        chapter_sentences = list(
            sentences_col.find({"chapter_id": chapter_id}).sort(
                [("chapter_number", 1), ("para_id", 1), ("order", 1)]
            )
        )
        nlp_updates = []
        parsed_by_id = {}
        nlp_started_at = perf_counter()
        for sent_doc, parsed in process_sentence_batch(chapter_sentences, batch_size=nlp_batch_size):
            parsed_by_id[sent_doc["_id"]] = parsed
            nlp_updates.append(UpdateOne({"_id": sent_doc["_id"]}, {"$set": parsed}))
        if nlp_updates:
            sentences_col.bulk_write(nlp_updates, ordered=True)
        logger.info(
            "chapter_nlp_done book_id=%s chapter_id=%s sentences=%s batch_size=%s elapsed_sec=%.3f",
            book_id,
            chapter_id,
            len(chapter_sentences),
            nlp_batch_size,
            perf_counter() - nlp_started_at,
        )

        fact_inserts = []
        for sent in chapter_sentences:
            parsed = parsed_by_id.get(sent["_id"])
            if parsed:
                sent.update(parsed)
            for fact in extract_facts(sent):
                fact_inserts.append(InsertOne(fact))
        if fact_inserts:
            facts_col.bulk_write(fact_inserts, ordered=True)

        chapter_facts = list(facts_col.find({"chapter_id": chapter_id}).sort("_id", 1))
        score_updates = [
            UpdateOne({"_id": fact["_id"]}, {"$set": {"score": score_fact(fact)}})
            for fact in chapter_facts
        ]
        if score_updates:
            facts_col.bulk_write(score_updates, ordered=True)

        mcq_count = _generate_chapter_mcqs(
            book_id=book_id,
            chapter_id=chapter_id,
            chapter_number=chapter_number,
            target=mcq_target,
        )
        fact_count = len(chapter_facts)
        logger.info(
            "chapter_done book_id=%s chapter_id=%s facts=%s mcqs=%s",
            book_id,
            chapter_id,
            fact_count,
            mcq_count,
        )
        return {"facts": fact_count, "mcqs": mcq_count}
    except Exception as e:
        books_col.update_one(
            {"_id": book_id},
            {"$set": {"status": "failed", "last_error": str(e), "updated_at": _utcnow()}},
        )
        logger.exception("chapter_failed book_id=%s chapter_id=%s", book_id, chapter_id)
        raise


def _finalize_mcqs(book_id: int, target: int) -> int:
    docs = list(
        mcqs_col.find({"book_id": book_id}).sort(
            [("quality", -1), ("chapter_number", 1), ("question", 1), ("correct_answer", 1), ("_id", 1)]
        )
    )
    if not docs:
        return 0

    keep = docs[:target]
    keep_ids = [d["_id"] for d in keep]
    if len(docs) > len(keep):
        mcqs_col.delete_many({"book_id": book_id, "_id": {"$nin": keep_ids}})
    return len(keep)


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
    workers: int | None = None,
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

        chapter_docs = list(chapters_col.find({"book_id": book_id}).sort("chapter_number", 1))
        if not chapter_docs:
            raise EmptyResultError("No chapters available after persistence.")

        settings = get_settings()
        configured = workers if workers is not None else settings.pipeline_workers
        max_workers = max(1, min(os.cpu_count() or 1, int(configured)))
        logger.info(
            "Starting chapter workers book_id=%s workers=%s chapters=%s",
            book_id,
            max_workers,
            len(chapter_docs),
        )

        failures = []
        with ProcessPoolExecutor(max_workers=max_workers, initializer=init_worker) as executor:
            futures = [executor.submit(process_chapter, chapter, mcq_target) for chapter in chapter_docs]
            for future in futures:
                try:
                    future.result()
                except Exception as e:  # pragma: no cover - safety net for process errors
                    failures.append(str(e))

        if failures:
            raise RuntimeError(f"Chapter processing failed: {' | '.join(failures)}")

        n = _finalize_mcqs(book_id, target=mcq_target)
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
            {"$set": {"status": "failed", "last_error": str(e), "updated_at": _utcnow()}},
        )
        raise
