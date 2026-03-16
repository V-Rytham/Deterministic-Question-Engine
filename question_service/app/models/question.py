from __future__ import annotations

from pydantic import BaseModel


class QuestionItem(BaseModel):
    question_id: str
    book_id: str
    isbn: str | None = None
    chapter: int
    question: str
    options: list[str]
    correct_index: int


class QuestionResponse(BaseModel):
    status: str
    isbn: str | None = None
    message: str | None = None
    questions: list[QuestionItem] | None = None
