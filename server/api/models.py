from __future__ import annotations

from pydantic import BaseModel, Field


class GenerateBody(BaseModel):
    book_id: int = Field(..., gt=0, description="Project Gutenberg book id")
    workers: int | None = Field(
        None,
        ge=1,
        le=16,
        description="Optional chapter worker override for this run; defaults to PIPELINE_WORKERS.",
    )


class McqOut(BaseModel):
    question: str
    options: list[str]
    correct_answer: str
    difficulty: str | None = None
    quality: float | None = None


class GenerateResponse(BaseModel):
    mcqs: list[McqOut]


class BookSearchResult(BaseModel):
    id: int
    title: str
    author: str
