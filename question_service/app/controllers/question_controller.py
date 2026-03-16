from __future__ import annotations

from question_service.app.services.isbn_question_service import IsbnQuestionService


class QuestionController:
    def __init__(self, service: IsbnQuestionService):
        self.service = service

    def get_questions(self, isbn: str, background_tasks) -> dict:
        result = self.service.handle_request(isbn=isbn, background_tasks=background_tasks)
        payload = {"status": result.status, "isbn": result.isbn}
        if result.message:
            payload["message"] = result.message
        if result.questions is not None:
            payload["questions"] = result.questions
        return payload
