from __future__ import annotations

from dataclasses import dataclass, field

from app.rag.retriever import RetrievalError, retrieve_document_chunks


@dataclass
class RagResult:
    context: str
    sources: list[str]
    raw_sources: list[dict] = field(default_factory=list)


def format_rag_context(results: list[dict]) -> str:
    if not results:
        return ""

    sections: list[str] = ["DOCUMENT KNOWLEDGE:"]
    for item in results:
        filename = item.get("filename", "unknown")
        page_number = item.get("page_number", "?")
        chunk_index = item.get("chunk_index")
        text = item.get("text", "").strip()
        if chunk_index is not None:
            sections.append(
                f"[Source: {filename}, page {page_number}, chunk {chunk_index}]\n{text}"
            )
        else:
            sections.append(f"[Source: {filename}, page {page_number}]\n{text}")

    sections.extend(
        [
            "",
            "STRICT RULES:",
            "- Use document context when answering document-related questions.",
            "- Do not invent facts that are not supported by retrieved context.",
            "- If the documents do not contain the answer, explicitly say that the available documents do not provide enough information.",
            "- Clearly distinguish retrieved document information from general conversation.",
            "- Do not override deterministic eligibility results.",
        ]
    )
    return "\n\n".join(sections)


def format_rag_sources(results: list[dict]) -> list[str]:
    sources: list[str] = []
    for item in results:
        filename = item.get("filename")
        page_number = item.get("page_number")
        chunk_index = item.get("chunk_index")
        if filename and page_number is not None and chunk_index is not None:
            sources.append(
                f"{filename} — page {page_number} — chunk {chunk_index}"
            )
        elif filename and page_number is not None:
            sources.append(f"{filename} — page {page_number}")
    return list(dict.fromkeys(sources))


def search_knowledge_base(query: str, top_k: int = 5) -> RagResult:
    try:
        results = retrieve_document_chunks(query, top_k=top_k)
    except RetrievalError:
        raise

    return RagResult(
        context=format_rag_context(results),
        sources=format_rag_sources(results),
        raw_sources=[
            {
                "filename": r.get("filename", ""),
                "page_number": int(r.get("page_number") or 0),
                "chunk_index": int(r.get("chunk_index") or 0),
            }
            for r in results
            if r.get("filename")
        ],
    )


def try_search_knowledge_base(query: str, top_k: int = 5) -> RagResult | None:
    try:
        result = search_knowledge_base(query, top_k=top_k)
    except RetrievalError:
        return None

    if not result.context:
        return None
    return result
