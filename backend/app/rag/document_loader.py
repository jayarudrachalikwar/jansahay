from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from pypdf import PdfReader


class DocumentLoadError(Exception):
    pass


@dataclass
class DocumentPage:
    filename: str
    page_number: int
    text: str


@dataclass
class LoadedDocument:
    filename: str
    document_id: str
    pages: list[DocumentPage]


def load_pdf_document(file_path: Path, document_id: str) -> LoadedDocument:
    if not file_path.exists():
        raise DocumentLoadError(f"Document not found: {file_path.name}")

    if file_path.suffix.lower() != ".pdf":
        raise DocumentLoadError(f"Unsupported document type: {file_path.name}")

    try:
        reader = PdfReader(str(file_path))
    except Exception as exc:
        raise DocumentLoadError(f"Unable to read PDF: {file_path.name}") from exc

    pages: list[DocumentPage] = []
    for index, page in enumerate(reader.pages, start=1):
        extracted = (page.extract_text() or "").strip()
        if extracted:
            pages.append(
                DocumentPage(
                    filename=file_path.name,
                    page_number=index,
                    text=extracted,
                )
            )

    if not pages:
        raise DocumentLoadError(f"No extractable text found in PDF: {file_path.name}")

    return LoadedDocument(
        filename=file_path.name,
        document_id=document_id,
        pages=pages,
    )
