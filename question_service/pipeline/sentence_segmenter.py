from __future__ import annotations

from question_service.pipeline.nlp import get_nlp


class SentenceSegmenter:
    def segment(self, chapter_text: str) -> list[tuple[int, str]]:
        nlp = get_nlp()
        doc = nlp(chapter_text)
        return [
            (index + 1, sent.text.strip())
            for index, sent in enumerate(doc.sents)
            if sent.text.strip()
        ]
