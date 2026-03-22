from __future__ import annotations

from pydantic import BaseModel, Field


class GenerateBody(BaseModel):
    book_id: int = Field(..., gt=0, description="Project Gutenberg book id")


class McqOut(BaseModel):
    question: str
    options: list[str]
    correct_answer: str
    difficulty: str | None = None
    quality: float | None = None


class GenerateResponse(BaseModel):
    mcqs: list[McqOut]

