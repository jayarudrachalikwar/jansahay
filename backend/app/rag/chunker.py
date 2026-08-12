from __future__ import annotations

from dataclasses import dataclass

from app.rag.document_loader import DocumentPage


@dataclass
class DocumentChunk:
    document_id: str
    filename: str
    page_number: int
    chunk_index: int
    text: str


def chunk_pages(
    *,
    document_id: str,
    pages: list[DocumentPage],
    target_words: int = 650,
    overlap_words: int = 75,
) -> list[DocumentChunk]:
    chunks: list[DocumentChunk] = []
    chunk_index = 0

    for page in pages:
        words = page.text.split()
        if not words:
            continue

        start = 0
        while start < len(words):
            end = min(start + target_words, len(words))
            chunk_words = words[start:end]
            if not chunk_words:
                break

            chunks.append(
                DocumentChunk(
                    document_id=document_id,
                    filename=page.filename,
                    page_number=page.page_number,
                    chunk_index=chunk_index,
                    text=" ".join(chunk_words),
                )
            )
            chunk_index += 1

            if end >= len(words):
                break
            start = max(end - overlap_words, start + 1)

    return chunks
