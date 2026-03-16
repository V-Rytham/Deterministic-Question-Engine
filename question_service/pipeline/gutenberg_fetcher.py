from __future__ import annotations

import re
from urllib.parse import urlparse

import requests

from question_service.config.settings import settings


class GutenbergFetcher:
    START_PATTERNS = [r"\*\*\* START OF (THE|THIS) PROJECT GUTENBERG EBOOK.*?\*\*\*"]
    END_PATTERNS = [r"\*\*\* END OF (THE|THIS) PROJECT GUTENBERG EBOOK.*?\*\*\*"]

    def fetch(self, book_url: str) -> tuple[str, str]:
        response = requests.get(book_url, timeout=settings.request_timeout_seconds)
        response.raise_for_status()
        text = response.text
        cleaned = self._strip_gutenberg_boilerplate(text)
        return self._derive_book_id(book_url), cleaned

    def _strip_gutenberg_boilerplate(self, text: str) -> str:
        start_idx = 0
        end_idx = len(text)

        for pattern in self.START_PATTERNS:
            match = re.search(pattern, text, flags=re.IGNORECASE | re.DOTALL)
            if match:
                start_idx = max(start_idx, match.end())

        for pattern in self.END_PATTERNS:
            match = re.search(pattern, text, flags=re.IGNORECASE | re.DOTALL)
            if match:
                end_idx = min(end_idx, match.start())

        return text[start_idx:end_idx].strip()

    @staticmethod
    def _derive_book_id(book_url: str) -> str:
        path = urlparse(book_url).path
        match = re.search(r"(\d+)", path)
        return match.group(1) if match else path.replace("/", "_").strip("_")
