from __future__ import annotations

from fastapi import APIRouter

from question_service.app.controllers.question_controller import QuestionController
from question_service.app.db.mongo import get_db
from question_service.app.models.question import QuestionResponse
from question_service.app.services.question_service import QuestionService

router = APIRouter()


@router.get("/questions/{book_id}", response_model=QuestionResponse)
def get_questions(book_id: str):
    controller = QuestionController(QuestionService(get_db()))
    return {"book_id": book_id, "questions": controller.get_questions(book_id)}
