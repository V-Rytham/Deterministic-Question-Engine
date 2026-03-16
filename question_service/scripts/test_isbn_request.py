from __future__ import annotations

import argparse
import json

import requests


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Test ISBN-driven /questions endpoint")
    parser.add_argument("--isbn", required=True)
    parser.add_argument("--base_url", default="http://127.0.0.1:8000")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    response = requests.get(f"{args.base_url}/questions/{args.isbn}", timeout=30)
    print(f"status_code={response.status_code}")
    print(json.dumps(response.json(), indent=2))


if __name__ == "__main__":
    main()
