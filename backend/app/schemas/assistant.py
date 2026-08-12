from typing import Literal

from pydantic import BaseModel, Field, field_validator


class ChatHistoryMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=4000)


class AssistantChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=2000)
    history: list[ChatHistoryMessage] = Field(default_factory=list, max_length=20)

    @field_validator("message")
    @classmethod
    def strip_message(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("Message cannot be empty")
        return stripped


class RagSourceItem(BaseModel):
    filename: str
    page_number: int
    chunk_index: int


class AssistantChatResponse(BaseModel):
    answer: str
    sources: list[str] = Field(default_factory=list)
    eligibility_checked: bool = False
    rag_sources: list[RagSourceItem] = Field(default_factory=list)
