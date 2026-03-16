from __future__ import annotations

import threading
from dataclasses import dataclass

from pymongo.database import Database

from question_service.app.services.isbn_catalog_service import IsbnCatalogService
from question_service.app.services.question_service import QuestionService
from question_service.pipeline.pipeline_runner import PipelineRunner


@dataclass
class IsbnRequestResult:
    status: str
    isbn: str
    message: str | None = None
    questions: list[dict] | None = None


class IsbnQuestionService:
    _lock = threading.Lock()
    _inflight: set[str] = set()

    def __init__(self, db: Database):
        self.db = db
        self.question_service = QuestionService(db)
        self.catalog = IsbnCatalogService()

    def handle_request(self, isbn: str, background_tasks) -> IsbnRequestResult:
        existing_questions = self.question_service.get_random_questions_by_isbn(isbn, limit=5)
        if existing_questions:
            return IsbnRequestResult(status="completed", isbn=isbn, questions=existing_questions)

        book = self.db.books.find_one({"isbn": isbn}, {"_id": 0})
        if book:
            status = book.get("pipeline_status", "pending")
            if status == "processing":
                return IsbnRequestResult(
                    status="processing",
                    isbn=isbn,
                    message="Questions are being generated. Try again shortly.",
                )

            self.db.books.update_one({"isbn": isbn}, {"$set": {"pipeline_status": "processing"}})
            self._enqueue_pipeline(background_tasks, isbn, book.get("source_url"), book.get("title"), book.get("author"))
            return IsbnRequestResult(
                status="processing",
                isbn=isbn,
                message="Questions are being generated. Try again shortly.",
            )

        resolved = self.catalog.resolve(isbn)
        if not resolved:
            return IsbnRequestResult(
                status="failed",
                isbn=isbn,
                message="Could not resolve ISBN to a Project Gutenberg source.",
            )

        self.db.books.update_one(
            {"isbn": isbn},
            {
                "$set": {
                    "isbn": isbn,
                    "title": resolved.title or f"ISBN {isbn}",
                    "author": resolved.author or "Unknown",
                    "source_url": resolved.book_url,
                    "pipeline_status": "processing",
                }
            },
            upsert=True,
        )

        self._enqueue_pipeline(background_tasks, isbn, resolved.book_url, resolved.title, resolved.author)
        return IsbnRequestResult(status="processing", isbn=isbn, message="Book is being processed.")

    def _enqueue_pipeline(self, background_tasks, isbn: str, book_url: str | None, title: str | None, author: str | None) -> None:
        if not book_url:
            self.db.books.update_one({"isbn": isbn}, {"$set": {"pipeline_status": "failed"}})
            return

        with self._lock:
            if isbn in self._inflight:
                return
            self._inflight.add(isbn)

        background_tasks.add_task(self._run_pipeline, isbn, book_url, title, author)

    def _run_pipeline(self, isbn: str, book_url: str, title: str | None, author: str | None) -> None:
        try:
            runner = PipelineRunner(self.db)
            runner.run(book_url=book_url, title=title, author=author, isbn=isbn)
            self.db.books.update_one({"isbn": isbn}, {"$set": {"pipeline_status": "completed"}})
        except Exception:
            self.db.books.update_one({"isbn": isbn}, {"$set": {"pipeline_status": "failed"}})
        finally:
            with self._lock:
                self._inflight.discard(isbn)
