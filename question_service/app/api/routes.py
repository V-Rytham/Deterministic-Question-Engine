from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks

from question_service.app.controllers.question_controller import QuestionController
from question_service.app.db.mongo import get_db
from question_service.app.services.isbn_question_service import IsbnQuestionService
from question_service.app.services.question_service import QuestionService

router = APIRouter()


@router.get("/questions/{isbn}")
def get_questions(isbn: str, background_tasks: BackgroundTasks):
    service = IsbnQuestionService(get_db())
    result = service.handle_request(isbn, background_tasks)

    if result.status == "completed":
        return {"status": "completed", "isbn": isbn, "questions": result.questions}

    if result.status == "unavailable":
        return {
            "status": "unavailable",
            "isbn": isbn,
            "message": "This book is not available in the public domain.",
        }

    return {"status": "processing", "isbn": isbn, "message": result.message or "Generating questions from the book..."}


@router.get("/questions/all/{isbn}")
def get_all_questions(isbn: str):
    controller = QuestionController(QuestionService(get_db()))
    return controller.get_all_questions_by_isbn(isbn)
