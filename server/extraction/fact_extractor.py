"""
Rule-based fact extraction from NLP-enriched sentences. Multiple facts per sentence allowed.
"""

from __future__ import annotations

import re
from typing import Optional

from server.db.mongo import sentences_col, facts_col

# Reject pronoun-only or weak referential phrases
PRONOUN_TOKENS = {
    "i",
    "me",
    "my",
    "we",
    "us",
    "our",
    "you",
    "your",
    "he",
    "him",
    "his",
    "she",
    "her",
    "hers",
    "they",
    "them",
    "their",
    "it",
    "its",
    "this",
    "that",
    "these",
    "those",
}


def _is_pronoun_phrase(text: str) -> bool:
    if not text:
        return True
    parts = re.findall(r"[A-Za-z']+", text.lower())
    if not parts:
        return True
    return all(p in PRONOUN_TOKENS for p in parts)


def _is_noisy_phrase(text: str) -> bool:
    """Reject OCR-like or structural fragments that produce unusable MCQs."""
    t = text.strip()
    if len(t) > 180:
        return True
    if len(t.split()) > 28:
        return True
    if t.count(",") > 4:
        return True
    if t.count("(") > 2 or t.count(")") > 2:
        return True
    if re.search(r"\[\d", t):
        return True
    if re.match(r"^[\s:;,\-\]\[\.]+", t):
        return True
    if t.startswith(":") or t.startswith("-") or t.startswith("]"):
        return True
    return False


def _too_weak(subject: str, obj: str) -> bool:
    if len(subject.strip()) < 2 or len(obj.strip()) < 2:
        return True
    if _is_pronoun_phrase(subject) or _is_pronoun_phrase(obj):
        return True
    if _is_noisy_phrase(subject) or _is_noisy_phrase(obj):
        return True
    return False


def _best_ner(phrase: str, entities) -> Optional[str]:
    if not phrase or not entities:
        return None
    pl = phrase.lower()
    best_label = None
    best_len = 0
    for e in entities:
        et = e["text"].lower()
        if et in pl and len(et) > best_len:
            best_label = e["label"]
            best_len = len(et)
    return best_label


def extract_facts(sent):
    subject = sent.get("subject")
    root_lemma = (sent.get("root_lemma") or "").lower()
    root_text = (sent.get("root") or "").lower()
    obj = sent.get("object")
    modifiers = sent.get("modifiers") or []
    entities = sent.get("entities") or []

    facts = []

    rel_surface = (sent.get("root") or root_text or root_lemma or "").strip()

    def push(subj, rel, ob, ftype, conf=0.7):
        if not subj or not ob or not rel:
            return
        if _too_weak(subj, ob):
            return
        facts.append(
            {
                "sentence_id": sent["_id"],
                "book_id": sent["book_id"],
                "chapter_id": sent["chapter_id"],
                "chapter_number": sent.get("chapter_number"),
                "subject": subj.strip(),
                "relation": rel,
                "relation_surface": rel_surface or rel,
                "object": ob.strip(),
                "type": ftype,
                "confidence": conf,
                "subject_ner": _best_ner(subj, entities),
                "object_ner": _best_ner(ob, entities),
            }
        )

    # Copula / attribute (X was a Y)
    if root_lemma == "be" and subject and obj:
        push(subject, "is_a", obj, "attribute", 0.82)

    # Active transitive (non-copula)
    if root_lemma and root_lemma != "be" and subject and obj:
        push(subject, root_lemma, obj, "active", 0.78)

    # Passive: agent in "by ..." maps to subject slot; patient stays object-like
    for mod in modifiers:
        ml = mod.lower()
        if ml.startswith("by ") and subject and root_lemma:
            agent = mod[3:].strip()
            if agent and not _is_pronoun_phrase(agent):
                push(agent, root_lemma, subject, "passive", 0.8)

    # Time-like modifiers (contains digits)
    for mod in modifiers:
        if any(ch.isdigit() for ch in mod):
            anchor = obj or subject
            if anchor and root_lemma:
                push(anchor, f"{root_lemma}_when", mod, "time", 0.72)

    # Intransitive + time in modifier only (e.g. "arrived in 1815")
    if not any(f["type"] == "time" for f in facts):
        for mod in modifiers:
            if any(ch.isdigit() for ch in mod) and subject and root_lemma and not obj:
                push(subject, f"{root_lemma}_when", mod, "time", 0.68)

    return facts


def run_fact_extraction(book_id):
    cursor = sentences_col.find({"book_id": book_id}).sort(
        [("chapter_number", 1), ("para_id", 1), ("order", 1)]
    )
    for sent in cursor:
        for fact in extract_facts(sent):
            facts_col.insert_one(fact)
    # Logging intentionally omitted here; pipeline logs progress.
