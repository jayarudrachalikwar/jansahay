import { useState } from "react";
import axios from "axios";
import ChatInput from "../../components/assistant/ChatInput";
import ChatMessage from "../../components/assistant/ChatMessage";
import VoiceRecorder from "../../components/voice/VoiceRecorder";
import VoicePlayback from "../../components/voice/VoicePlayback";
import LanguageSelector from "../../components/voice/LanguageSelector";
import { sendAssistantMessage } from "../../services/assistantService";
import { voiceChat, type SupportedLanguage } from "../../services/voiceService";
import type { ChatMessage as ChatMessageType } from "../../types/assistant";

const SUGGESTED_QUESTIONS = [
  "Which schemes are suitable for me?",
  "Show schemes related to irrigation.",
  "Why am I eligible for this scheme?",
  "What information is in my farmer profile?",
];

interface MessageWithAudio extends ChatMessageType {
  audioBase64?: string;
  transcript?: string;
}

function getErrorMessage(error: unknown): string {
  if (axios.isAxiosError(error)) {
    const detail = error.response?.data?.detail;
    if (typeof detail === "string") return detail;
  }
  return "Unable to reach the AI assistant. Please try again.";
}

export default function AssistantPage() {
  const [messages, setMessages] = useState<MessageWithAudio[]>([]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [language, setLanguage] = useState<SupportedLanguage>("en");

  async function submitTextMessage(messageText: string) {
    const trimmed = messageText.trim();
    if (!trimmed || isLoading) return;

    const userMessage: MessageWithAudio = { role: "user", content: trimmed };
    const nextMessages = [...messages, userMessage];
    setMessages(nextMessages);
    setInput("");
    setError(null);
    setIsLoading(true);

    try {
      const response = await sendAssistantMessage({
        message: trimmed,
        history: messages.map((m) => ({ role: m.role, content: m.content })),
      });
      setMessages([
        ...nextMessages,
        { role: "assistant", content: response.answer },
      ]);
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setIsLoading(false);
    }
  }

  async function handleVoiceRecording(audioBlob: Blob) {
    if (isLoading) return;
    setError(null);
    setIsLoading(true);

    try {
      const result = await voiceChat(
        audioBlob,
        language,
        messages.map((m) => ({ role: m.role, content: m.content })),
      );

      const userMessage: MessageWithAudio = {
        role: "user",
        content: result.transcript,
        transcript: result.transcript,
      };
      const assistantMessage: MessageWithAudio = {
        role: "assistant",
        content: result.response_text,
        audioBase64: result.audio_base64 ?? undefined,
      };

      setMessages((prev) => [...prev, userMessage, assistantMessage]);
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setIsLoading(false);
    }
  }

  function handleClearConversation() {
    setMessages([]);
    setInput("");
    setError(null);
  }

  return (
    <div className="mx-auto max-w-4xl px-4 py-12">
      <section className="rounded-2xl border border-slate-200 bg-white p-8 shadow-sm">
        <p className="text-sm font-medium uppercase tracking-wide text-emerald-700">
          AI Assistant
        </p>
        <h1 className="mt-2 text-2xl font-bold text-slate-900">
          Government Scheme Assistant
        </h1>
        <p className="mt-2 text-sm text-slate-600">
          Ask questions about schemes in JanSahay by typing or speaking.
          Eligibility results come from the configured rules engine.
        </p>

        {/* Language selector + clear button */}
        <div className="mt-4 flex flex-wrap items-center justify-between gap-3">
          <LanguageSelector
            value={language}
            onChange={setLanguage}
            disabled={isLoading}
          />
          <button
            type="button"
            onClick={handleClearConversation}
            disabled={messages.length === 0 && !error}
            className="rounded-lg border border-slate-300 px-3 py-1.5 text-sm font-medium text-slate-700 transition hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-60"
          >
            Clear Conversation
          </button>
        </div>

        {/* Message list */}
        <div className="mt-6 min-h-[320px] space-y-4 rounded-xl border border-slate-200 bg-slate-50 p-4">
          {messages.length === 0 && !error && (
            <p className="text-center text-sm text-slate-500">
              Start a conversation, choose a suggested question, or use 🎤 to speak.
            </p>
          )}

          {messages.map((message, index) => (
            <div key={`${message.role}-${index}`}>
              {message.role === "user" && message.transcript && (
                <p className="mb-1 flex items-center gap-1 text-xs text-slate-400">
                  <span>🎤</span>
                  <span>Voice input</span>
                </p>
              )}
              <ChatMessage message={message} />
              {message.role === "assistant" && message.audioBase64 && (
                <div className="mt-1.5 ml-1">
                  <VoicePlayback audioBase64={message.audioBase64} label="Play response" />
                </div>
              )}
            </div>
          ))}

          {isLoading && (
            <p className="text-sm text-slate-500">Assistant is preparing a response…</p>
          )}
        </div>

        {error && (
          <p className="mt-4 rounded-lg border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">
            {error}
          </p>
        )}

        {/* Input area: voice recorder + text input */}
        <div className="mt-6">
          <div className="mb-3 flex items-center gap-3">
            <VoiceRecorder
              onRecordingComplete={handleVoiceRecording}
              isDisabled={isLoading}
            />
            <p className="text-xs text-slate-500">
              Press 🎤 to speak, or type below.
            </p>
          </div>

          <ChatInput
            value={input}
            onChange={setInput}
            onSubmit={() => submitTextMessage(input)}
            isLoading={isLoading}
            suggestedQuestions={SUGGESTED_QUESTIONS}
            onSuggestedQuestion={(question) => {
              setInput(question);
              submitTextMessage(question);
            }}
          />
        </div>
      </section>
    </div>
  );
}
