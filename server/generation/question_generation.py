"""
Template-based question generation from scored facts (deterministic templates).
"""

from __future__ import annotations

from typing import Any


def _looks_like_person(subj: str) -> bool:
    parts = subj.strip().split()
    return len(parts) <= 4 and parts and parts[0][:1].isupper()


def generate_question_variants(fact: dict[str, Any]) -> list[dict[str, Any]]:
    """
    Each variant: { "kind": str, "question": str, "correct": str, "answer_role": "subject"|"object" }
    """
    subj = fact.get("subject") or ""
    obj = fact.get("object") or ""
    if len(subj) + len(obj) > 220:
        return []
    rel = fact.get("relation") or ""
    rel_s = (fact.get("relation_surface") or rel or "").strip()
    ftype = fact.get("type")
    subj_ner = fact.get("subject_ner")
    variants: list[dict[str, Any]] = []

    if ftype == "attribute" or rel == "is_a":
        variants.append(
            {
                "kind": "attribute",
                "question": f"In the text, how is {subj} described?",
                "correct": obj,
                "answer_role": "object",
            }
        )
        variants.append(
            {
                "kind": "fill_blank",
                "question": f"_____ is described in the text as {obj}.",
                "correct": subj,
                "answer_role": "subject",
            }
        )
        return variants

    if ftype == "time":
        variants.append(
            {
                "kind": "when",
                "question": f"According to the text, what time expression is linked to {subj}?",
                "correct": obj,
                "answer_role": "object",
            }
        )
        variants.append(
            {
                "kind": "relation_when",
                "question": f"In the passage, when is {subj} associated with the described event?",
                "correct": obj,
                "answer_role": "object",
            }
        )
        return variants

    # Active / passive narrative facts
    person_focus = subj_ner == "PERSON" or _looks_like_person(subj)
    if person_focus:
        variants.append(
            {
                "kind": "direct_who",
                "question": f"According to the book, who {rel_s} {obj}?",
                "correct": subj,
                "answer_role": "subject",
            }
        )
    else:
        variants.append(
            {
                "kind": "direct_what_subject",
                "question": f"According to the book, who or what {rel_s} {obj}?",
                "correct": subj,
                "answer_role": "subject",
            }
        )

    variants.append(
        {
            "kind": "reverse",
            "question": f"According to the text, {subj} {rel_s} what?",
            "correct": obj,
            "answer_role": "object",
        }
    )

    variants.append(
        {
            "kind": "fill_blank",
            "question": f"_____ {rel_s} {obj}, according to the text.",
            "correct": subj,
            "answer_role": "subject",
        }
    )

    return variants


def difficulty_for(fact: dict[str, Any], variant_kind: str) -> str:
    base = float(fact.get("score") or 0.0)
    if base >= 5.5:
        tier = "hard"
    elif base >= 3.5:
        tier = "medium"
    else:
        tier = "easy"
    if variant_kind in ("reverse", "relation_when"):
        tier = "hard" if tier == "medium" else tier
    return tier
