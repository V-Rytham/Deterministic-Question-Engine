from __future__ import annotations

from dataclasses import dataclass
from difflib import SequenceMatcher
from urllib.parse import quote_plus

import requests
from pymongo.database import Database

from question_service.config.settings import settings


@dataclass
class ResolvedBook:
    isbn: str
    gutenberg_id: str | None
    title: str | None = None
    author: str | None = None
    confidence_score: float = 0.0

    @property
    def book_url(self) -> str | None:
        if not self.gutenberg_id:
            return None
        return f"https://www.gutenberg.org/cache/epub/{self.gutenberg_id}/pg{self.gutenberg_id}.txt"


class IsbnCatalogService:
    OPEN_LIBRARY_URL = "https://openlibrary.org/api/books?bibkeys=ISBN:{isbn}&format=json&jscmd=data"
    GUTENDEX_URL = "https://gutendex.com/books/?search={query}"

    DEFAULT_SOURCE_MAP = {
        "9780141439518": {
            "gutenberg_id": "1342",
            "title": "Pride and Prejudice",
            "author": "Jane Austen",
            "confidence_score": 1.0,
        },
        "9780141439600": {
            "gutenberg_id": "1342",
            "title": "Pride and Prejudice",
            "author": "Jane Austen",
            "confidence_score": 1.0,
        },
    }

    def __init__(self, db: Database):
        self.db = db

    def resolve(self, isbn: str) -> ResolvedBook | None:
        cached = self.db.isbn_gutenberg_map.find_one({"isbn": isbn}, {"_id": 0})
        if cached:
            return ResolvedBook(
                isbn=isbn,
                gutenberg_id=cached.get("gutenberg_id"),
                title=cached.get("title"),
                author=cached.get("author"),
                confidence_score=float(cached.get("confidence_score") or 0.0),
            )

        from_env = settings.isbn_source_map.get(isbn) or self.DEFAULT_SOURCE_MAP.get(isbn)
        if isinstance(from_env, dict) and from_env.get("gutenberg_id"):
            resolved = ResolvedBook(
                isbn=isbn,
                gutenberg_id=str(from_env["gutenberg_id"]),
                title=from_env.get("title"),
                author=from_env.get("author"),
                confidence_score=float(from_env.get("confidence_score") or 1.0),
            )
            self._persist_mapping(resolved)
            return resolved

        metadata = self._lookup_open_library(isbn)
        if not metadata:
            self._persist_mapping(ResolvedBook(isbn=isbn, gutenberg_id=None, confidence_score=0.0))
            return None

        match = self._search_gutenberg(metadata["title"], metadata.get("author"))
        if not match:
            self._persist_mapping(
                ResolvedBook(
                    isbn=isbn,
                    gutenberg_id=None,
                    title=metadata.get("title"),
                    author=metadata.get("author"),
                    confidence_score=0.0,
                )
            )
            return None

        resolved = ResolvedBook(
            isbn=isbn,
            gutenberg_id=match["gutenberg_id"],
            title=match.get("title") or metadata.get("title"),
            author=match.get("author") or metadata.get("author"),
            confidence_score=match.get("confidence_score", 0.0),
        )
        self._persist_mapping(resolved)
        return resolved

    def _persist_mapping(self, resolved: ResolvedBook) -> None:
        self.db.isbn_gutenberg_map.update_one(
            {"isbn": resolved.isbn},
            {
                "$set": {
                    "isbn": resolved.isbn,
                    "gutenberg_id": resolved.gutenberg_id,
                    "title": resolved.title,
                    "author": resolved.author,
                    "confidence_score": round(float(resolved.confidence_score), 4),
                }
            },
            upsert=True,
        )

    def _lookup_open_library(self, isbn: str) -> dict | None:
        response = requests.get(
            self.OPEN_LIBRARY_URL.format(isbn=isbn),
            timeout=settings.request_timeout_seconds,
        )
        if response.status_code != 200:
            return None

        payload = response.json()
        data = payload.get(f"ISBN:{isbn}")
        if not isinstance(data, dict):
            return None

        title = (data.get("title") or "").strip()
        if not title:
            return None

        author = None
        authors = data.get("authors")
        if isinstance(authors, list) and authors:
            primary_author = authors[0]
            if isinstance(primary_author, dict):
                author = (primary_author.get("name") or "").strip() or None

        return {"title": title, "author": author}

    def _search_gutenberg(self, title: str, author: str | None) -> dict | None:
        response = requests.get(
            self.GUTENDEX_URL.format(query=quote_plus(title)),
            timeout=settings.request_timeout_seconds,
        )
        if response.status_code != 200:
            return None

        payload = response.json()
        results = payload.get("results", [])
        if not isinstance(results, list):
            return None

        best_match = None
        best_score = 0.0
        for candidate in results:
            if not isinstance(candidate, dict):
                continue

            cand_title = str(candidate.get("title") or "")
            authors = candidate.get("authors") or []
            cand_author = None
            if isinstance(authors, list) and authors:
                first_author = authors[0]
                if isinstance(first_author, dict):
                    cand_author = str(first_author.get("name") or "")

            title_score = self._similarity(title, cand_title)
            author_score = self._similarity(author, cand_author) if author else 0.5
            score = (0.75 * title_score) + (0.25 * author_score)
            if score > best_score:
                best_score = score
                best_match = {
                    "gutenberg_id": str(candidate.get("id")),
                    "title": cand_title,
                    "author": cand_author,
                    "confidence_score": score,
                }

        if best_match and best_score >= 0.55:
            return best_match
        return None

    @staticmethod
    def _similarity(left: str | None, right: str | None) -> float:
        if not left or not right:
            return 0.0
        return SequenceMatcher(None, left.lower().strip(), right.lower().strip()).ratio()
