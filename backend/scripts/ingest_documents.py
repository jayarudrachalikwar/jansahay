"""Ingest local PDF documents into the Qdrant knowledge base."""

from __future__ import annotations

import sys
from pathlib import Path

from app.rag.chunker import chunk_pages
from app.rag.document_loader import DocumentLoadError, load_pdf_document
from app.rag.embeddings import (
    EmbeddingAPIError,
    EmbeddingNotConfiguredError,
    generate_embeddings_batch,
)
from app.rag.vector_store import (
    VectorStoreOperationError,
    VectorStoreUnavailableError,
    compute_document_id,
    get_qdrant_client,
    upsert_chunks,
)

DOCUMENTS_DIR = Path(__file__).resolve().parents[1] / "data" / "documents"
SAMPLE_PDF = DOCUMENTS_DIR / "sample_crop_insurance.pdf"


def ensure_sample_pdf() -> None:
    if SAMPLE_PDF.exists():
        return
    from scripts.create_sample_pdf import main as create_sample

    create_sample()


def ingest_documents() -> int:
    ensure_sample_pdf()

    pdf_files = sorted(DOCUMENTS_DIR.glob("*.pdf"))
    if not pdf_files:
        print(
            f"No PDF documents found in {DOCUMENTS_DIR}. "
            "Add development PDF files before running ingestion.",
            file=sys.stderr,
        )
        return 1

    print(f"Found {len(pdf_files)} document(s)")

    try:
        client = get_qdrant_client()
    except VectorStoreUnavailableError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    total_chunks = 0
    processed_documents = 0

    for pdf_path in pdf_files:
        print(f"Processing: {pdf_path.name}")
        file_bytes = pdf_path.read_bytes()
        document_id = compute_document_id(pdf_path.name, file_bytes)

        try:
            loaded = load_pdf_document(pdf_path, document_id=document_id)
        except DocumentLoadError as exc:
            print(f"  Skipped: {exc}", file=sys.stderr)
            continue

        print(f"  Extracted {len(loaded.pages)} pages")
        chunks = chunk_pages(document_id=document_id, pages=loaded.pages)
        print(f"  Created {len(chunks)} chunks")

        if not chunks:
            print("  Skipped: no chunks created", file=sys.stderr)
            continue

        texts = [chunk.text for chunk in chunks]
        try:
            embeddings = generate_embeddings_batch(texts)
        except (EmbeddingNotConfiguredError, EmbeddingAPIError) as exc:
            print(str(exc), file=sys.stderr)
            return 1

        print("  Generated embeddings")
        try:
            indexed = upsert_chunks(client, chunks, embeddings)
        except VectorStoreOperationError as exc:
            print(str(exc), file=sys.stderr)
            return 1

        print(f"  Indexed {indexed} chunks")
        total_chunks += indexed
        processed_documents += 1

    if processed_documents == 0:
        print("Ingestion failed: no documents were indexed.", file=sys.stderr)
        return 1

    print("\nIngestion complete.")
    print(f"Total documents: {processed_documents}")
    print(f"Total chunks indexed: {total_chunks}")
    return 0


def main() -> int:
    return ingest_documents()


if __name__ == "__main__":
    raise SystemExit(main())
