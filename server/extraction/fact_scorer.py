"""
Deterministic fact quality scoring (no ML). Updates `score` on each fact document.
"""

import re
from server.db.mongo import facts_col

NAMED_LABELS = {"PERSON", "ORG", "GPE", "LOC", "FAC", "EVENT", "PRODUCT", "WORK_OF_ART", "NORP", "LAW", "LANGUAGE"}


def score_fact(doc: dict) -> float:
    score = 0.0

    subj_ner = doc.get("subject_ner")
    obj_ner = doc.get("object_ner")
    if subj_ner in NAMED_LABELS:
        score += 2.0
    if obj_ner in NAMED_LABELS:
        score += 1.5

    rel = (doc.get("relation") or "").lower()
    if rel and rel not in ("is_a", "be"):
        score += 0.8
    if rel == "is_a":
        score += 0.5

    subj = doc.get("subject") or ""
    obj = doc.get("object") or ""
    # Object completeness (length without being noisy)
    score += min(1.5, len(obj.split()) * 0.15)
    score += min(1.2, len(subj.split()) * 0.12)

    # Specificity: capitalized tokens / digits
    if re.search(r"\d{4}", obj):
        score += 0.4
    if re.search(r"[A-Z][a-z]+", subj + " " + obj):
        score += 0.2

    ftype = doc.get("type")
    weights = {"active": 0.15, "passive": 0.12, "attribute": 0.1, "time": 0.18}
    score += weights.get(ftype, 0.05)

    conf = float(doc.get("confidence") or 0.7)
    score += (conf - 0.7) * 2.0

    return round(score, 4)


def run_fact_scoring(book_id):
    for fact in facts_col.find({"book_id": book_id}):
        s = score_fact(fact)
        facts_col.update_one({"_id": fact["_id"]}, {"$set": {"score": s}})

    # Logging intentionally omitted here; pipeline logs progress.
