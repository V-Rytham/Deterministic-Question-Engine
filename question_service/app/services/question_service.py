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

    def get_random_questions_by_isbn(self, isbn: str, limit: int = 5) -> list[dict]:
        book = self.db.books.find_one({"isbn": isbn}, {"_id": 0, "book_id": 1})
        if not book or not book.get("book_id"):
            return []
        return self.get_random_questions(book["book_id"], limit=limit)

    def get_all_questions_by_isbn(self, isbn: str, limit: int = 100) -> list[dict]:
        book = self.db.books.find_one({"isbn": isbn}, {"_id": 0, "book_id": 1})
        if not book or not book.get("book_id"):
            return []

        cursor = self.db.book_questions.find(
            {"book_id": book["book_id"]},
            {"_id": 0, "question": 1, "options": 1, "correct_index": 1},
        ).limit(limit)
        return list(cursor)
