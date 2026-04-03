from __future__ import annotations

import argparse
import logging
from itertools import islice

from requests import RequestException

from server.db.mongo import books_index_col
from server.ingestion.books_index import (
    bulk_upsert_books_index,
    ensure_books_index_indexes,
    iter_gutendex_books,
)

logger = logging.getLogger(__name__)


def _chunked(iterable, size: int):
    iterator = iter(iterable)
    while True:
        chunk = list(islice(iterator, size))
        if not chunk:
            return
        yield chunk


def main() -> None:
    parser = argparse.ArgumentParser(description="Populate local Gutenberg books_index")
    parser.add_argument(
        "--pages",
        type=int,
        default=20,
        help="Number of Gutendex pages to index (default: 20)",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=200,
        help="Bulk insert batch size (default: 200)",
    )
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    ensure_books_index_indexes(books_index_col)

    total_seen = 0
    total_inserted = 0

    try:
        books_stream = iter_gutendex_books(page_limit=args.pages)
        for batch in _chunked(books_stream, args.batch_size):
            total_seen += len(batch)
            inserted = bulk_upsert_books_index(books_index_col, batch)
            total_inserted += inserted
            logger.info(
                "Indexed batch size=%s inserted=%s total_seen=%s total_inserted=%s",
                len(batch),
                inserted,
                total_seen,
                total_inserted,
            )
    except RequestException:
        logger.exception("Failed to fetch metadata from Gutendex")
        raise

    logger.info(
        "Done indexing books. processed=%s inserted=%s duplicates_skipped=%s",
        total_seen,
        total_inserted,
        total_seen - total_inserted,
    )


if __name__ == "__main__":
    main()
