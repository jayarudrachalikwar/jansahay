import type { ChatMessage } from "../../types/assistant";

interface ChatMessageProps {
  message: ChatMessage;
}

export default function ChatMessage({ message }: ChatMessageProps) {
  const isUser = message.role === "user";

  return (
    <div className={`flex ${isUser ? "justify-end" : "justify-start"}`}>
      <div
        className={`max-w-[85%] rounded-2xl px-4 py-3 text-sm leading-relaxed ${
          isUser
            ? "bg-emerald-700 text-white"
            : "border border-slate-200 bg-white text-slate-800 shadow-sm"
        }`}
      >
        <p className="mb-1 text-xs font-semibold uppercase tracking-wide opacity-80">
          {isUser ? "You" : "JanSahay Assistant"}
        </p>
        <p className="whitespace-pre-wrap">{message.content}</p>
      </div>
    </div>
  );
}
