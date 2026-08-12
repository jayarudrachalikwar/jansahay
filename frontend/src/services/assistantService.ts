import api from "./api";
import type { AssistantChatRequest, AssistantChatResponse } from "../types/assistant";

export async function sendAssistantMessage(
  payload: AssistantChatRequest,
): Promise<AssistantChatResponse> {
  const response = await api.post<AssistantChatResponse>("/api/assistant/chat", payload);
  return response.data;
}
