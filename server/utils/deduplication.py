"""
Semantic deduplication of MCQ prompts using TF-IDF cosine similarity (deterministic).
"""

from __future__ import annotations

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


def dedupe_questions(mcqs: list[dict], similarity_threshold: float = 0.88) -> list[dict]:
    """
    Keep higher-quality items first; drop later items that are too similar to an already kept question.
    """
    if len(mcqs) <= 1:
        return mcqs

    ordered = sorted(mcqs, key=lambda m: -float(m.get("quality") or 0.0))
    texts = [m["question"] for m in ordered]
    vec = TfidfVectorizer(max_features=4096, ngram_range=(1, 2))
    X = vec.fit_transform(texts)

    kept: list[dict] = []
    kept_rows: list[int] = []

    for i, m in enumerate(ordered):
        if not kept_rows:
            kept.append(m)
            kept_rows.append(i)
            continue
        sims = cosine_similarity(X[i : i + 1], X[kept_rows])
        if sims.size and sims.max() >= similarity_threshold:
            continue
        kept.append(m)
        kept_rows.append(i)

    kept.sort(key=lambda x: -float(x.get("quality") or 0.0))
    return kept

