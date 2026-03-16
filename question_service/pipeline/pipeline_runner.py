from __future__ import annotations

from collections import Counter

from pymongo.database import Database

from question_service.pipeline.chapter_splitter import ChapterSplitter
from question_service.pipeline.dependency_parser import DependencyParser
from question_service.pipeline.distractor_generator import DistractorGenerator
from question_service.pipeline.fact_builder import Fact
from question_service.pipeline.fact_builder import FactBuilder
from question_service.pipeline.fact_filter import FactFilter
from question_service.pipeline.gutenberg_fetcher import GutenbergFetcher
from question_service.pipeline.mcq_generator import McqGenerator
from question_service.pipeline.ner_extractor import NerExtractor
from question_service.pipeline.sentence_segmenter import SentenceSegmenter


class PipelineRunner:
    def __init__(self, db: Database):
        self.db = db
        self.fetcher = GutenbergFetcher()
        self.chapter_splitter = ChapterSplitter()
        self.segmenter = SentenceSegmenter()
        self.ner = NerExtractor()
        self.dep = DependencyParser()
        self.fact_builder = FactBuilder()
        self.fact_filter = FactFilter()
        self.mcq_generator = McqGenerator()
        self.distractor_generator = DistractorGenerator()

    def run(self, book_url: str, title: str | None = None, author: str | None = None) -> dict:
        book_id, text = self.fetcher.fetch(book_url)
        chapters = self.chapter_splitter.split(text)

        all_facts: list[Fact] = []
        all_entities = []

        for chapter_num, chapter_text in chapters:
            for position, sentence in self.segmenter.segment(chapter_text):
                entities = self.ner.extract(sentence)
                parsed = self.dep.parse(sentence)
                all_entities.extend(entities)
                all_facts.extend(
                    self.fact_builder.build(
                        book_id=book_id,
                        chapter=chapter_num,
                        sentence=sentence,
                        position=position,
                        parsed_cores=parsed,
                        entities=entities,
                    )
                )

        entity_freq: Counter = self.ner.frequency_map(all_entities)
        filtered = self.fact_filter.filter(all_facts, dict(entity_freq))

        self._persist_book(book_id, title, author, book_url)
        self._persist_entities(book_id, entity_freq)
        self._persist_facts(book_id, filtered)
        question_count = self._persist_questions(book_id, filtered)

        return {
            "book_id": book_id,
            "chapters": len(chapters),
            "facts_total": len(all_facts),
            "facts_filtered": len(filtered),
            "questions": question_count,
        }

    def _persist_book(self, book_id: str, title: str | None, author: str | None, source_url: str) -> None:
        self.db.books.update_one(
            {"book_id": book_id},
            {
                "$set": {
                    "book_id": book_id,
                    "title": title or f"Gutenberg {book_id}",
                    "author": author or "Unknown",
                    "source_url": source_url,
                }
            },
            upsert=True,
        )

    def _persist_entities(self, book_id: str, entity_freq: Counter) -> None:
        for (entity, entity_type), frequency in entity_freq.items():
            self.db.entity_bank.update_one(
                {"book_id": book_id, "entity": entity},
                {
                    "$set": {"book_id": book_id, "entity": entity, "entity_type": entity_type},
                    "$inc": {"frequency": int(frequency)},
                },
                upsert=True,
            )

    def _persist_facts(self, book_id: str, facts: list[Fact]) -> None:
        self.db.book_facts.delete_many({"book_id": book_id})
        if facts:
            self.db.book_facts.insert_many([fact.to_dict() for fact in facts])

    def _persist_questions(self, book_id: str, facts: list[Fact]) -> int:
        self.db.book_questions.delete_many({"book_id": book_id})
        entities = list(self.db.entity_bank.find({"book_id": book_id}, {"_id": 0}))
        generated = []
        for fact in facts:
            drafts = self.mcq_generator.generate(fact)
            for draft in drafts:
                question = self.distractor_generator.build_question(
                    book_id,
                    draft,
                    entities,
                    subject=fact.subject,
                    obj=fact.object,
                )
                if question:
                    generated.append(question.to_dict())

        if generated:
            self.db.book_questions.insert_many(generated)
        return len(generated)
