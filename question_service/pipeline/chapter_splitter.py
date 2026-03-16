from __future__ import annotations

import re
from typing import List


class ChapterSplitter:
    """Split Gutenberg text into semantic chapters while avoiding front-matter noise."""

    CHAPTER_REGEX = re.compile(
        r"(?im)^\s*(?:chapter\s+(?:[ivxlcdm\d]+|one|two|three|four|five|six|seven|eight|nine|ten)\b[^\n]*|book\s+[ivxlcdm\d]+\b[^\n]*)$"
    )
    NOISE_REGEX = re.compile(r"(?im)^\s*(?:volume\s+[ivxlcdm\d]+|contents|table of contents)\s*$")

    def split(self, text: str) -> List[tuple[int, str]]:
        """Return numbered chapters; fallback to single chapter when no markers are found."""
        matches = [m for m in self.CHAPTER_REGEX.finditer(text) if not self.NOISE_REGEX.match(m.group(0))]
        if not matches:
            return [(1, text.strip())]

        chapters: list[tuple[int, str]] = []
        for idx, match in enumerate(matches):
            start = match.start()
            end = matches[idx + 1].start() if idx + 1 < len(matches) else len(text)
            chapter_text = text[start:end].strip()
            if chapter_text and len(chapter_text.split()) >= 6:
                chapters.append((idx + 1, chapter_text))

        return chapters or [(1, text.strip())]
