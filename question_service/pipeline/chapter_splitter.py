from __future__ import annotations

import re
from typing import List


class ChapterSplitter:
    CHAPTER_REGEX = re.compile(
        r"(?im)^\s*(chapter\s+[ivxlcdm\d]+\b.*)$",
    )

    def split(self, text: str) -> List[tuple[int, str]]:
        matches = list(self.CHAPTER_REGEX.finditer(text))
        if not matches:
            return [(1, text.strip())]

        chapters: list[tuple[int, str]] = []
        for idx, match in enumerate(matches):
            start = match.start()
            end = matches[idx + 1].start() if idx + 1 < len(matches) else len(text)
            chapter_text = text[start:end].strip()
            if chapter_text:
                chapters.append((idx + 1, chapter_text))

        return chapters or [(1, text.strip())]
