from __future__ import annotations

from pymongo.database import Database


class QuestionService:
    def __init__(self, db: Database):
        self.db = db

    def get_random_questions(self, book_id: str, limit: int = 5) -> list[dict]:
        # Backward compatible helper for existing book_id consumers.
        book_id_candidates: list[str | int] = [book_id]
        if book_id.isdigit():
            book_id_candidates.append(int(book_id))
        return self._sample_questions({"book_id": {"$in": book_id_candidates}}, limit=limit)

    def get_random_questions_by_isbn(self, isbn: str, limit: int = 5) -> list[dict]:
        return self._sample_questions({"isbn": isbn}, limit=limit)

    def _sample_questions(self, match_filter: dict, limit: int) -> list[dict]:
        pipeline = [
            {"$match": match_filter},
            {"$sample": {"size": limit}},
            {
                "$project": {
                    "_id": 0,
                    "question_id": 1,
                    "book_id": 1,
                    "isbn": 1,
                    "chapter": 1,
                    "question": 1,
                    "options": 1,
                    "correct_index": 1,
                }
            },
        ]
        return list(self.db.book_questions.aggregate(pipeline))
