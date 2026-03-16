from __future__ import annotations

import random
import uuid
from dataclasses import dataclass

from question_service.pipeline.mcq_generator import QuestionDraft


@dataclass
class GeneratedQuestion:
    question_id: str
    book_id: str
    chapter: int
    fact_id: str
    question: str
    options: list[str]
    correct_index: int

    def to_dict(self) -> dict:
        return {
            "question_id": self.question_id,
            "book_id": self.book_id,
            "chapter": self.chapter,
            "fact_id": self.fact_id,
            "question": self.question,
            "options": self.options,
            "correct_index": self.correct_index,
        }


class DistractorGenerator:
    """Construct 4-option MCQs with type-compatible distractors."""

    def build_question(
        self,
        book_id: str,
        draft: QuestionDraft,
        entity_bank: list[dict],
        subject: str,
        obj: str,
    ) -> GeneratedQuestion | None:
        blocked = {draft.answer.strip().lower(), subject.strip().lower(), obj.strip().lower()}
        pool = []
        seen = set()

        for item in entity_bank:
            entity = str(item.get("entity") or "").strip()
            entity_type = str(item.get("entity_type") or "")
            freq = int(item.get("frequency", 0) or 0)
            if not entity or entity.lower() in blocked:
                continue
            if entity_type != draft.answer_type:
                continue
            if freq < 3:
                continue
            if entity.lower() in seen:
                continue
            seen.add(entity.lower())
            pool.append(entity)

        if len(pool) < 3:
            return None

        distractors = random.sample(pool, 3)
        options = distractors + [draft.answer]
        random.shuffle(options)
        return GeneratedQuestion(
            question_id=str(uuid.uuid4()),
            book_id=book_id,
            chapter=draft.chapter,
            fact_id=draft.fact_id,
            question=draft.question,
            options=options,
            correct_index=options.index(draft.answer),
        )
