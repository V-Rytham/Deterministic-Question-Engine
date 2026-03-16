from __future__ import annotations

from pydantic import BaseModel


class QuestionItem(BaseModel):
    question_id: str
    book_id: str
    chapter: int
    question: str
    options: list[str]
    correct_index: int


class QuestionResponse(BaseModel):
    book_id: str
    questions: list[QuestionItem]
