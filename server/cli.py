import argparse

from server.db.mongo import facts_col, mcqs_col
from server.pipeline import run_pipeline


def _print_sample_mcqs(book_id: int, limit: int = 5) -> None:
    rows = list(mcqs_col.find({"book_id": book_id}).limit(limit))
    for i, m in enumerate(rows, 1):
        print(f"\n--- MCQ {i} ---")
        print(m.get("question"))
        for j, opt in enumerate(m.get("options") or [], 1):
            mark = "*" if opt == m.get("correct_answer") else " "
            print(f"  {mark} {j}. {opt}")
        print(f"  difficulty={m.get('difficulty')}  quality={m.get('quality')}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Deterministic Question Generator pipeline")
    parser.add_argument("book_id", type=int, nargs="?", default=8438, help="Gutenberg book id")
    parser.add_argument("--target", type=int, default=100, help="MCQ target count")
    args = parser.parse_args()

    n = run_pipeline(args.book_id, mcq_target=args.target)
    fc = facts_col.count_documents({"book_id": args.book_id})
    print(f"\nValidation: facts_extracted={fc}, mcqs_generated={n}")
    _print_sample_mcqs(args.book_id, 5)
