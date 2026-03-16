from __future__ import annotations

from fastapi import HTTPException

from question_service.app.services.question_service import QuestionService


class QuestionController:
    def __init__(self, service: QuestionService):
        self.service = service

    def get_questions(self, book_id: str) -> list[dict]:
        questions = self.service.get_random_questions(book_id, limit=5)
        if not questions:
            raise HTTPException(status_code=404, detail=f"No questions found for book_id '{book_id}'")
        return questions

    def get_all_questions_by_isbn(self, isbn: str) -> list[dict]:
        questions = self.service.get_all_questions_by_isbn(isbn, limit=100)
        if not questions:
            raise HTTPException(status_code=404, detail=f"No questions found for isbn '{isbn}'")
        return questions
