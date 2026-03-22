"""
Plausible wrong answers: same coarse entity class where possible (NER label buckets).
Fully deterministic selection order.
"""

from __future__ import annotations

from typing import Any, Optional


def _bucket_for_role(fact: dict[str, Any], answer_role: str) -> Optional[str]:
    if answer_role == "subject":
        return fact.get("subject_ner") or "MISC"
    if answer_role == "object":
        return fact.get("object_ner") or "MISC"
    return "MISC"


def _pool_string_ok(val: str) -> bool:
    v = val.strip()
    if len(v) > 120 or len(v.split()) > 22:
        return False
    if v.count(",") > 3:
        return False
    if v.startswith(":") or v.startswith("-") or v.startswith("]"):
        return False
    if "[" in v or "]" in v:
        return False
    return True


def build_pools(facts: list[dict[str, Any]]) -> dict[str, list[str]]:
    """Map NER bucket -> distinct answer strings seen in facts."""
    pools: dict[str, set[str]] = {}
    for f in facts:
        for label_key, field in (
            ("subject_ner", "subject"),
            ("object_ner", "object"),
        ):
            lab = f.get(label_key) or "MISC"
            val = (f.get(field) or "").strip()
            if not val or not _pool_string_ok(val):
                continue
            pools.setdefault(lab, set()).add(val)
    return {k: sorted(v) for k, v in pools.items()}


def _acceptable_distractor(correct: str, cand: str) -> bool:
    if not cand or cand.strip().lower() == correct.strip().lower():
        return False
    c = cand.strip()
    if len(cand) > max(90, len(correct) * 3):
        return False
    if len(cand.split()) > 24:
        return False
    if cand.count(",") > 3:
        return False
    if c.startswith(":") or c.startswith("-") or "[" in c or "]" in c:
        return False
    return True


def pick_distractors(
    correct: str,
    bucket: Optional[str],
    pools: dict[str, list[str]],
    book_facts: list[dict[str, Any]],
    need: int = 3,
) -> list[str]:
    """Pick `need` distractors, same bucket first, then neighboring buckets."""
    correct_l = correct.strip().lower()
    out: list[str] = []

    def try_pool(keys: list[str]):
        for key in keys:
            for cand in pools.get(key, []):
                cl = cand.strip().lower()
                if cl == correct_l or cand in out:
                    continue
                if not _acceptable_distractor(correct, cand):
                    continue
                out.append(cand)
                if len(out) >= need:
                    return True
        return False

    order_keys = []
    if bucket and bucket in pools:
        order_keys.append(bucket)
    for k in sorted(pools.keys()):
        if k not in order_keys:
            order_keys.append(k)

    try_pool(order_keys)

    if len(out) < need:
        # Fallback: any other subject/object strings from facts
        flat: list[str] = []
        for f in book_facts:
            for field in ("subject", "object"):
                t = (f.get(field) or "").strip()
                if t and t.lower() != correct_l and _acceptable_distractor(correct, t):
                    flat.append(t)
        flat = sorted(set(flat), key=str.lower)
        for t in flat:
            if t in out:
                continue
            out.append(t)
            if len(out) >= need:
                break

    if len(out) < need:
        # Last resort: pad with truncated variants (still deterministic)
        pad_i = 1
        while len(out) < need:
            candidate = f"Alternative detail #{pad_i}"
            if candidate.lower() != correct_l:
                out.append(candidate)
            pad_i += 1

    return out[:need]
