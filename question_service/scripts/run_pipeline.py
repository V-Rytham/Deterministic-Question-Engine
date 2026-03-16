from __future__ import annotations

import argparse
import json

from question_service.app.db.mongo import ensure_indexes, get_db
from question_service.pipeline.pipeline_runner import PipelineRunner


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run offline MCQ generation pipeline")
    parser.add_argument("--book_url", required=True, help="Project Gutenberg text URL")
    parser.add_argument("--isbn", default=None, help="Optional ISBN to link generated data")
    parser.add_argument("--title", default=None)
    parser.add_argument("--author", default=None)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    ensure_indexes()
    runner = PipelineRunner(get_db())
    summary = runner.run(book_url=args.book_url, isbn=args.isbn, title=args.title, author=args.author)
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
