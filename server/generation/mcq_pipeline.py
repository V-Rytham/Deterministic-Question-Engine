"""
Assemble MCQs from scored facts: distractors, deterministic shuffling, dedupe, final pick.
"""

from __future__ import annotations

import logging

from server.db.mongo import books_col, facts_col, mcqs_col
from server.generation.deterministic_shuffle import stable_option_order
from server.generation.distractors import build_pools, pick_distractors, _bucket_for_role
from server.generation.question_generation import difficulty_for, generate_question_variants
from server.utils.deduplication import dedupe_questions
from server.utils.selection import select_top_mcqs

logger = logging.getLogger(__name__)


def _quality(fact: dict, variant_kind: str) -> float:
    base = float(fact.get("score") or 0.0)
    bonus = 0.2 if variant_kind in ("direct_who", "attribute") else 0.0
    return round(base + bonus, 4)


def run_mcq_generation(book_id: int, target: int = 100) -> int:
    mcqs_col.delete_many({"book_id": book_id})

    facts = list(facts_col.find({"book_id": book_id}).sort("score", -1))
    if not facts:
        logger.warning("No facts available for MCQ generation (book_id=%s).", book_id)
        return 0

    pools = build_pools(facts)

    # Cap work: high-scoring facts first; each fact contributes at most 2 variants
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
            all_opts = [correct] + distractors
            seed = f"{fact['_id']}:{v['kind']}"
            options = stable_option_order(all_opts, seed)

            diff = difficulty_for(fact, v["kind"])
            qdoc = {
                "book_id": book_id,
                "chapter_number": fact.get("chapter_number"),
                "question": v["question"],
                "options": options,
                "correct_answer": correct,
                "difficulty": diff,
                "source_fact_id": fact["_id"],
                "quality": _quality(fact, v["kind"]),
                "variant_kind": v["kind"],
            }
            candidates.append(qdoc)

    candidates = dedupe_questions(candidates, similarity_threshold=0.88)
    final = select_top_mcqs(candidates, k=target)

    for doc in final:
        mcqs_col.insert_one(doc)

    books_col.update_one(
        {"_id": book_id},
        {"$set": {"status": "completed", "mcq_count": len(final)}},
    )

    logger.info("MCQ generation stored %s items (target %s).", len(final), target)
    return len(final)
