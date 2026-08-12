from fastapi import APIRouter, Depends, HTTPException, status

from app.ai.neo4j.client import GraphDatabaseError, GraphDatabaseUnavailableError
from app.ai.neo4j.repository import get_graph_context_for_query
from app.auth.dependencies import get_current_user
from app.models.user import User
from app.rag.graph_rag_service import GraphRagResult, graph_rag_search
from app.rag.rag_service import try_search_knowledge_base
from app.rag.retriever import RetrievalError, retrieve_document_chunks
from app.schemas.rag import (
    GraphRagRequest,
    GraphRagResponse,
    GraphSearchRequest,
    GraphSearchResponse,
    RagSearchRequest,
    RagSearchResponse,
    RagSearchResultItem,
)

router = APIRouter(prefix="/rag", tags=["rag"])


@router.post("/search", response_model=RagSearchResponse)
def search_documents(
    payload: RagSearchRequest,
    current_user: User = Depends(get_current_user),
) -> RagSearchResponse:
    try:
        results = retrieve_document_chunks(payload.query, top_k=payload.top_k)
    except RetrievalError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc

    formatted = [
        RagSearchResultItem(
            text=item.get("text", ""),
            filename=item.get("filename", ""),
            page_number=int(item.get("page_number") or 0),
            chunk_index=int(item.get("chunk_index") or 0),
            score=float(item.get("score") or 0.0),
        )
        for item in results
    ]

    if not formatted:
        return RagSearchResponse(results=[], total=0)

    return RagSearchResponse(results=formatted, total=len(formatted))


@router.post("/graph-search", response_model=GraphSearchResponse)
def graph_search(
    payload: GraphSearchRequest,
    current_user: User = Depends(get_current_user),
) -> GraphSearchResponse:
    """
    Perform a Neo4j graph search for schemes matching the given
    state and/or crop context.  Returns structured graph context —
    no LLM inference is applied here.

    This endpoint is for testing and admin inspection.
    """
    try:
        results = get_graph_context_for_query(
            state=payload.state or None,
            crop=payload.crop or None,
            scheme_ids=payload.scheme_ids or [],
        )
    except GraphDatabaseUnavailableError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Graph database is unavailable.",
        ) from exc
    except GraphDatabaseError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Graph query failed.",
        ) from exc

    return GraphSearchResponse(results=results, total=len(results))


@router.post("/graph-rag", response_model=GraphRagResponse)
def graph_rag(
    payload: GraphRagRequest,
    current_user: User = Depends(get_current_user),
) -> GraphRagResponse:
    """
    Perform fused Qdrant vector + Neo4j graph retrieval for a query.
    Returns the combined context string, sources, and provenance.

    This endpoint is for testing and admin inspection.
    The full chat experience uses the assistant endpoint.
    """
    result: GraphRagResult = graph_rag_search(
        payload.query,
        state=payload.state or None,
        crop=payload.crop or None,
        scheme_ids=payload.scheme_ids or [],
        top_k=payload.top_k,
    )

    return GraphRagResponse(
        context=result.context,
        sources=result.sources,
        raw_sources=result.raw_sources,
        graph_used=result.graph_used,
        vector_used=result.vector_used,
    )
