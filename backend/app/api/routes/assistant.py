from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.database.session import get_db
from app.models.user import User
from app.schemas.assistant import AssistantChatRequest, AssistantChatResponse, RagSourceItem
from app.services.assistant_service import (
    GeminiAPIError,
    GeminiNotConfiguredError,
    process_assistant_chat,
)

router = APIRouter(prefix="/assistant", tags=["assistant"])


@router.post("/chat", response_model=AssistantChatResponse)
def assistant_chat(
    payload: AssistantChatRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> AssistantChatResponse:
    history = [{"role": item.role, "content": item.content} for item in payload.history]

    try:
        result = process_assistant_chat(
            db,
            current_user,
            payload.message,
            history=history,
        )
    except GeminiNotConfiguredError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc
    except GeminiAPIError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc

    return AssistantChatResponse(
        answer=result.answer,
        sources=result.sources,
        eligibility_checked=result.eligibility_checked,
        rag_sources=[
            RagSourceItem(
                filename=item["filename"],
                page_number=item["page_number"],
                chunk_index=item["chunk_index"],
            )
            for item in result.rag_sources
        ],
    )
