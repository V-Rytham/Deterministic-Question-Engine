from __future__ import annotations

from pymongo.database import Database


class QuestionService:
    def __init__(self, db: Database):
        self.db = db

    def get_random_questions(self, book_id: str, limit: int = 5) -> list[dict]:
        pipeline = [
            {"$match": {"book_id": book_id}},
            {"$sample": {"size": limit}},
            {
                "$project": {
                    "_id": 0,
                    "question_id": 1,
                    "book_id": 1,
                    "chapter": 1,
                    "question": 1,
                    "options": 1,
                    "correct_index": 1,
                }
            },
        ]
        return list(self.db.book_questions.aggregate(pipeline))
