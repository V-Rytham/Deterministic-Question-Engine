from __future__ import annotations

import re

from fastapi import APIRouter, BackgroundTasks, HTTPException

from question_service.app.controllers.question_controller import QuestionController
from question_service.app.db.mongo import get_db
from question_service.app.services.isbn_question_service import IsbnQuestionService
from question_service.app.services.question_service import QuestionService

router = APIRouter()
ISBN_REGEX = re.compile(r"^(?:\d{10}|\d{13})$")


def _normalize_isbn(value: str) -> str:
    cleaned = value.replace("-", "").strip()
    if not ISBN_REGEX.match(cleaned):
        raise HTTPException(status_code=422, detail="ISBN must be a 10 or 13 digit number.")
    return cleaned


@router.get("/questions/{isbn}")
def get_questions(isbn: str, background_tasks: BackgroundTasks):
    normalized_isbn = _normalize_isbn(isbn)
    service = IsbnQuestionService(get_db())
    result = service.handle_request(normalized_isbn, background_tasks)

    if result.status == "completed":
        return {"status": "completed", "isbn": normalized_isbn, "questions": result.questions}

    if result.status == "unavailable":
        return {
            "status": "unavailable",
            "isbn": normalized_isbn,
            "message": "This book is not available in the public domain.",
        }

    return {
        "status": "processing",
        "isbn": normalized_isbn,
        "message": result.message or "Generating questions from the book...",
    }


@router.get("/questions/all/{isbn}")
def get_all_questions(isbn: str):
    normalized_isbn = _normalize_isbn(isbn)
    controller = QuestionController(QuestionService(get_db()))
    return controller.get_all_questions_by_isbn(normalized_isbn)
