from __future__ import annotations

import argparse
import json

from question_service.app.db.mongo import get_db
from question_service.app.services.question_service import QuestionService


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Fetch 5 random questions for a book")
    parser.add_argument("--book_id", required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    service = QuestionService(get_db())
    questions = service.get_random_questions(args.book_id, limit=5)
    print(json.dumps(questions, indent=2))


if __name__ == "__main__":
    main()
