from __future__ import annotations

import logging
import re
import string
from typing import Any

import requests
from pymongo import TEXT, InsertOne
from pymongo.collection import Collection
from pymongo.errors import BulkWriteError
from requests import RequestException
from requests import ReadTimeout

logger = logging.getLogger(__name__)

_GUTENDEX_URL = "https://gutendex.com/books/"
_PUNCTUATION_TRANSLATION = str.maketrans({c: " " for c in string.punctuation})
_EXTERNAL_SEARCH_MIN_QUERY_LENGTH = 5


def ensure_books_index_indexes(collection: Collection) -> None:
    """Ensure indexes exist for local book search."""
    collection.create_index("book_id", unique=True)
    collection.create_index([("search_text", TEXT)])


def normalize_search_text(raw: str) -> str:
    lowered = raw.lower().translate(_PUNCTUATION_TRANSLATION)
    normalized = re.sub(r"\s+", " ", lowered).strip()
    return normalized


def _primary_author(raw_authors: list[dict[str, Any]]) -> str:
    if not raw_authors:
        return "Unknown Author"
    name = str(raw_authors[0].get("name") or "").strip()
    return name or "Unknown Author"


def to_index_document(book: dict[str, Any]) -> dict[str, Any] | None:
    if not book.get("id"):
        return None

    book_id = int(book["id"])
    title = str(book.get("title") or "Untitled").strip() or "Untitled"
    author = _primary_author(book.get("authors") or [])
    search_text = normalize_search_text(f"{title} {author}")

    return {
        "book_id": book_id,
        "title": title,
        "author": author,
        "search_text": search_text,
    }


def bulk_upsert_books_index(collection: Collection, books: list[dict[str, Any]]) -> int:
    docs = [d for d in (to_index_document(book) for book in books) if d]
    if not docs:
        return 0

    ops = [
        InsertOne(doc)
        for doc in docs
    ]

    inserted = 0
    try:
        result = collection.bulk_write(ops, ordered=False)
        inserted = result.inserted_count
    except BulkWriteError as exc:
        write_errors = exc.details.get("writeErrors") or []
        duplicate_errors = [e for e in write_errors if e.get("code") == 11000]
        non_duplicates = [e for e in write_errors if e.get("code") != 11000]

        if non_duplicates:
            raise

        inserted = len(docs) - len(duplicate_errors)

    return inserted


def fetch_from_gutendex(query: str, timeout: int = 8) -> list[dict[str, Any]]:
    res = requests.get(_GUTENDEX_URL, params={"search": query}, timeout=timeout)
    res.raise_for_status()
    payload = res.json()
    return payload.get("results") or []


def iter_gutendex_books(page_limit: int | None = None, timeout: int = 20):
    page_url: str | None = _GUTENDEX_URL
    pages_fetched = 0

    while page_url:
        if page_limit is not None and pages_fetched >= page_limit:
            break

        res = requests.get(page_url, timeout=timeout)
        res.raise_for_status()
        payload = res.json()

        for book in (payload.get("results") or []):
            yield book

        page_url = payload.get("next")
        pages_fetched += 1


def search_books_index(collection: Collection, query: str, limit: int = 8) -> list[dict[str, Any]]:
    normalized = normalize_search_text(query)
    if not normalized:
        return []

    cursor = (
        collection.find(
            {"$text": {"$search": normalized}},
            {
                "_id": 0,
                "book_id": 1,
                "title": 1,
                "author": 1,
                "score": {"$meta": "textScore"},
            },
        )
        .sort([("score", {"$meta": "textScore"})])
        .limit(limit)
    )

    results = list(cursor)
    if results:
        return results

    regex = re.escape(normalized)
    regex_cursor = collection.find(
        {"search_text": {"$regex": rf"\\b{regex}", "$options": "i"}},
        {"_id": 0, "book_id": 1, "title": 1, "author": 1},
    ).limit(limit)
    return list(regex_cursor)


def fetch_and_cache_external(
    collection: Collection,
    query: str,
    limit: int = 8,
) -> list[dict[str, Any]]:
    if len(normalize_search_text(query)) < _EXTERNAL_SEARCH_MIN_QUERY_LENGTH:
        return []

    try:
        external = fetch_from_gutendex(query)
    except ReadTimeout:
        logger.warning(
            "Fallback Gutendex search timed out for query=%s (timeout=%ss)",
            query,
            8,
        )
        return []
    except RequestException:
        logger.exception("Fallback Gutendex search failed for query=%s", query)
        return []

    if external:
        try:
            inserted = bulk_upsert_books_index(collection, external)
            logger.info(
                "Cached %s external books for query=%s",
                inserted,
                query,
            )
        except Exception:
            logger.exception("Failed caching fallback books for query=%s", query)

    output = []
    for book in external[:limit]:
        doc = to_index_document(book)
        if doc is None:
            continue
        output.append(doc)

    return output
