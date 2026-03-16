from __future__ import annotations

from dataclasses import dataclass

import requests

from question_service.config.settings import settings


@dataclass
class ResolvedBook:
    isbn: str
    book_url: str
    title: str | None = None
    author: str | None = None


class IsbnCatalogService:
    OPEN_LIBRARY_URL = "https://openlibrary.org/isbn/{isbn}.json"

    DEFAULT_SOURCE_MAP = {
        "9780141439518": {
            "book_url": "https://www.gutenberg.org/cache/epub/1342/pg1342.txt",
            "title": "Pride and Prejudice",
            "author": "Jane Austen",
        },
        "9780141439600": {
            "book_url": "https://www.gutenberg.org/cache/epub/1342/pg1342.txt",
            "title": "Pride and Prejudice",
            "author": "Jane Austen",
        },
    }

    def resolve(self, isbn: str) -> ResolvedBook | None:
        from_env = settings.isbn_source_map.get(isbn) or self.DEFAULT_SOURCE_MAP.get(isbn)
        if isinstance(from_env, dict) and from_env.get("book_url"):
            return ResolvedBook(
                isbn=isbn,
                book_url=from_env["book_url"],
                title=from_env.get("title"),
                author=from_env.get("author"),
            )

        return self._resolve_from_openlibrary(isbn)

    def _resolve_from_openlibrary(self, isbn: str) -> ResolvedBook | None:
        response = requests.get(
            self.OPEN_LIBRARY_URL.format(isbn=isbn),
            timeout=settings.request_timeout_seconds,
        )
        if response.status_code != 200:
            return None

        payload = response.json()
        identifiers = payload.get("identifiers", {})
        gutenberg_ids = identifiers.get("project_gutenberg") or identifiers.get("gutenberg") or []
        if not gutenberg_ids:
            return None

        gutenberg_id = str(gutenberg_ids[0]).strip()
        if not gutenberg_id:
            return None

        title = payload.get("title")
        author = None
        by_statement = payload.get("by_statement")
        if isinstance(by_statement, str) and by_statement.strip():
            author = by_statement.strip()

        return ResolvedBook(
            isbn=isbn,
            book_url=f"https://www.gutenberg.org/cache/epub/{gutenberg_id}/pg{gutenberg_id}.txt",
            title=title,
            author=author,
        )
