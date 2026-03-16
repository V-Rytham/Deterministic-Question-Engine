from __future__ import annotations

from pymongo.database import Database


class QuestionService:
    def __init__(self, db: Database):
        self.db = db

    def get_random_questions(self, book_id: str, limit: int = 5) -> list[dict]:
        # Be tolerant to historical data where `book_id` may have been stored
        # as an integer (e.g. 1342) instead of a string ("1342").
        book_id_candidates: list[str | int] = [book_id]
        if book_id.isdigit():
            book_id_candidates.append(int(book_id))

        pipeline = [
            {"$match": {"book_id": {"$in": book_id_candidates}}},
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
