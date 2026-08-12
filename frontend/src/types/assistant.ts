export type ChatRole = "user" | "assistant";

export interface ChatMessage {
  role: ChatRole;
  content: string;
}

export interface AssistantChatRequest {
  message: string;
  history?: ChatMessage[];
}

export interface RagSourceItem {
  filename: string;
  page_number: number;
  chunk_index: number;
}

export interface AssistantChatResponse {
  answer: string;
  sources: string[];
  eligibility_checked: boolean;
  rag_sources: RagSourceItem[];
}
