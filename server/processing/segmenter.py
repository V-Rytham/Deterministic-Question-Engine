import re

from server.db.mongo import paragraphs_col, sentences_col
from server.processing.spacy_model import get_nlp


def clean_text(text):
    text = re.sub(r"\n+", " ", text)
    text = re.sub(r"_+", "", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def split_paragraphs(text):
    paragraphs = re.split(r"\n\s*\n", text)
    return [p.strip() for p in paragraphs if len(p.strip()) > 80]


def segment_chapter(chapter_doc):
    chapter_id = chapter_doc["_id"]
    book_id = chapter_doc["book_id"]
    chapter_number = chapter_doc.get("chapter_number", 0)
    raw_text = chapter_doc["text"]

    paragraphs = split_paragraphs(raw_text)

    for p_idx, para in enumerate(paragraphs):
        para = clean_text(para)
        if len(para) < 80:
            continue

        para_doc = {
            "chapter_id": chapter_id,
            "book_id": book_id,
            "chapter_number": chapter_number,
            "text": para,
            "order": p_idx,
        }

        para_id = paragraphs_col.insert_one(para_doc).inserted_id

        doc = get_nlp()(para)

        for s_idx, sent in enumerate(doc.sents):
            sent_text = sent.text.strip()
            if len(sent_text) < 20:
                continue

            sentences_col.insert_one(
                {
                    "para_id": para_id,
                    "chapter_id": chapter_id,
                    "book_id": book_id,
                    "chapter_number": chapter_number,
                    "text": sent_text,
                    "order": s_idx,
                    "resolved_text": None,
                }
            )
