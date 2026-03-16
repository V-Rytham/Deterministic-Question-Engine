from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks

from question_service.app.controllers.question_controller import QuestionController
from question_service.app.db.mongo import get_db
from question_service.app.models.question import QuestionResponse
from question_service.app.services.isbn_question_service import IsbnQuestionService

router = APIRouter()


@router.get("/questions/{isbn}", response_model=QuestionResponse)
def get_questions(isbn: str, background_tasks: BackgroundTasks):
    controller = QuestionController(IsbnQuestionService(get_db()))
    return controller.get_questions(isbn=isbn, background_tasks=background_tasks)
