from __future__ import annotations

import unittest

from question_service.pipeline.chapter_splitter import ChapterSplitter
from question_service.pipeline.dependency_parser import ParsedFactCore
from question_service.pipeline.distractor_generator import DistractorGenerator
from question_service.pipeline.fact_builder import FactBuilder
from question_service.pipeline.fact_filter import FactFilter
from question_service.pipeline.mcq_generator import McqGenerator, QuestionDraft
from question_service.pipeline.ner_extractor import EntityRecord


class PipelineComponentTests(unittest.TestCase):
    def test_chapter_splitter_handles_roman_arabic_and_word_markers(self):
        text = """
        CHAPTER I
        First chapter text has enough words for parsing and extraction to occur safely.

        Chapter 2
        Second chapter has enough words as well and should be separated.

        Chapter One
        Third chapter content continues with adequate sentence length for validation.
        """
        parts = ChapterSplitter().split(text)
        self.assertEqual(3, len(parts))

    def test_fact_builder_and_filter(self):
        builder = FactBuilder()
        cores = [ParsedFactCore(subject="Atticus Finch", verb="defended", object="Tom Robinson", lemma="defend")]
        entities = [
            EntityRecord(entity="Atticus Finch", entity_type="PERSON", sentence="Atticus Finch defended Tom Robinson in court."),
            EntityRecord(entity="Tom Robinson", entity_type="PERSON", sentence="Atticus Finch defended Tom Robinson in court."),
        ]
        facts = builder.build(
            book_id="123",
            chapter=1,
            sentence="Atticus Finch defended Tom Robinson in court with conviction.",
            position=1,
            parsed_cores=cores,
            entities=entities,
        )
        self.assertGreaterEqual(len(facts), 1)

        freq = {("Atticus Finch", "PERSON"): 3, ("Tom Robinson", "PERSON"): 3}
        filtered = FactFilter().filter(facts, freq)
        self.assertGreaterEqual(len(filtered), 1)

    def test_mcq_and_distractor_generation(self):
        draft = QuestionDraft(
            question="Who defended Tom Robinson?",
            answer="Atticus Finch",
            answer_type="PERSON",
            fact_id="f1",
            chapter=1,
        )
        entity_bank = [
            {"entity": "Heck Tate", "entity_type": "PERSON", "frequency": 5},
            {"entity": "Boo Radley", "entity_type": "PERSON", "frequency": 4},
            {"entity": "Judge Taylor", "entity_type": "PERSON", "frequency": 3},
            {"entity": "Atticus Finch", "entity_type": "PERSON", "frequency": 10},
        ]
        result = DistractorGenerator().build_question(
            "123",
            draft,
            entity_bank,
            subject="Atticus Finch",
            obj="Tom Robinson",
        )
        self.assertIsNotNone(result)
        self.assertEqual(4, len(result.options))
        self.assertIn("Atticus Finch", result.options)

    def test_mcq_generator_person_template(self):
        from question_service.pipeline.fact_builder import Fact

        fact = Fact(
            fact_id="f1",
            book_id="123",
            chapter=1,
            entity="Atticus Finch",
            entity_type="PERSON",
            lemma="defend",
            subject="Atticus Finch",
            verb="defended",
            object="Tom Robinson",
            sentence="Atticus Finch defended Tom Robinson in court.",
            position=1,
        )
        drafts = McqGenerator().generate(fact)
        self.assertTrue(any(d.question.startswith("Who") for d in drafts))


if __name__ == "__main__":
    unittest.main()
