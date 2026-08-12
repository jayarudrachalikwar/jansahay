import api from "./api";

export type SupportedLanguage = "en" | "hi" | "te";

export interface TranscribeResponse {
  transcript: string;
  language: string;
}

export interface VoiceChatResponse {
  transcript: string;
  language: string;
  response_text: string;
  audio_base64: string | null;
  sources: string[];
  eligibility_checked: boolean;
  rag_sources: { filename: string; page_number: number; chunk_index: number }[];
  tts_available: boolean;
}

export interface ProfileExtractResponse {
  raw_transcript: string;
  extracted_fields: Record<string, string>;
  uncertain_fields: string[];
}

export async function transcribeAudio(
  audioBlob: Blob,
  language: SupportedLanguage = "en",
): Promise<TranscribeResponse> {
  const mimeType = audioBlob.type || "audio/webm";
  const extension = mimeType.includes("ogg") ? ".ogg" : mimeType.includes("mp4") ? ".mp4" : ".webm";
  const formData = new FormData();
  formData.append("audio", audioBlob, `recording${extension}`);
  formData.append("language", language);
  const response = await api.post<TranscribeResponse>("/api/voice/transcribe", formData, {
    headers: { "Content-Type": undefined },
  });
  return response.data;
}

export async function speakText(
  text: string,
  language: SupportedLanguage = "en",
): Promise<Blob> {
  const response = await api.post(
    "/api/voice/speak",
    { text, language },
    { responseType: "blob" },
  );
  return response.data as Blob;
}

export async function voiceChat(
  audioBlob: Blob,
  language: SupportedLanguage = "en",
  history: { role: string; content: string }[] = [],
): Promise<VoiceChatResponse> {
  const mimeType = audioBlob.type || "audio/webm";
  const extension = mimeType.includes("ogg") ? ".ogg" : mimeType.includes("mp4") ? ".mp4" : ".webm";
  const filename = `recording${extension}`;

  console.log("[VOICE] Sending /api/voice/chat");
  console.log("[VOICE] Language:", language);
  console.log("[VOICE] Blob MIME type:", mimeType);
  console.log("[VOICE] Blob size:", audioBlob.size);

  const formData = new FormData();
  formData.append("audio", audioBlob, filename);
  formData.append("language", language);
  formData.append("history", JSON.stringify(history));

  // IMPORTANT: do NOT set Content-Type manually for FormData.
  // The browser must generate the multipart boundary automatically.
  // Axios's global "Content-Type: application/json" default would override
  // the multipart boundary — so we explicitly clear it for this request.
  const response = await api.post<VoiceChatResponse>("/api/voice/chat", formData, {
    headers: { "Content-Type": undefined },
  });

  console.log("[VOICE] Response status:", response.status);
  console.log("[VOICE] Transcript:", response.data.transcript);
  console.log("[VOICE] Assistant response:", response.data.response_text?.slice(0, 80));

  return response.data;
}

export async function extractProfileFromVoice(
  audioBlob: Blob,
  language: SupportedLanguage = "en",
): Promise<ProfileExtractResponse> {
  const mimeType = audioBlob.type || "audio/webm";
  const extension = mimeType.includes("ogg") ? ".ogg" : mimeType.includes("mp4") ? ".mp4" : ".webm";
  const formData = new FormData();
  formData.append("audio", audioBlob, `recording${extension}`);
  formData.append("language", language);
  const response = await api.post<ProfileExtractResponse>(
    "/api/voice/extract-profile",
    formData,
    { headers: { "Content-Type": undefined } },
  );
  return response.data;
}

/** Decode a base64 audio string to an Audio element-playable URL */
export function base64ToAudioUrl(base64: string): string {
  const binary = atob(base64);
  const bytes = new Uint8Array(binary.length);
  for (let i = 0; i < binary.length; i++) {
    bytes[i] = binary.charCodeAt(i);
  }
  const blob = new Blob([bytes], { type: "audio/mpeg" });
  return URL.createObjectURL(blob);
}
