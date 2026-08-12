import { FormEvent } from "react";

interface ChatInputProps {
  value: string;
  onChange: (value: string) => void;
  onSubmit: () => void;
  isLoading: boolean;
  suggestedQuestions: string[];
  onSuggestedQuestion: (question: string) => void;
}

export default function ChatInput({
  value,
  onChange,
  onSubmit,
  isLoading,
  suggestedQuestions,
  onSuggestedQuestion,
}: ChatInputProps) {
  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!value.trim() || isLoading) {
      return;
    }
    onSubmit();
  }

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap gap-2">
        {suggestedQuestions.map((question) => (
          <button
            key={question}
            type="button"
            onClick={() => onSuggestedQuestion(question)}
            disabled={isLoading}
            className="rounded-full border border-slate-300 bg-white px-3 py-1.5 text-xs font-medium text-slate-700 transition hover:border-emerald-600 hover:text-emerald-700 disabled:cursor-not-allowed disabled:opacity-60"
          >
            {question}
          </button>
        ))}
      </div>

      <form onSubmit={handleSubmit} className="flex gap-3">
        <label htmlFor="assistant-message" className="sr-only">
          Ask the assistant
        </label>
        <input
          id="assistant-message"
          type="text"
          value={value}
          onChange={(event) => onChange(event.target.value)}
          placeholder="Ask about government welfare schemes..."
          disabled={isLoading}
          className="flex-1 rounded-lg border border-slate-300 px-4 py-2 text-sm disabled:bg-slate-100"
        />
        <button
          type="submit"
          disabled={isLoading || !value.trim()}
          className="rounded-lg bg-emerald-700 px-4 py-2 text-sm font-medium text-white transition hover:bg-emerald-800 disabled:cursor-not-allowed disabled:opacity-70"
        >
          {isLoading ? "Sending..." : "Send"}
        </button>
      </form>
    </div>
  );
}
