import type { SupportedLanguage } from "../../services/voiceService";

interface LanguageSelectorProps {
  value: SupportedLanguage;
  onChange: (lang: SupportedLanguage) => void;
  disabled?: boolean;
}

const LANGUAGE_OPTIONS: { code: SupportedLanguage; label: string }[] = [
  { code: "en", label: "English" },
  { code: "hi", label: "हिन्दी" },
  { code: "te", label: "తెలుగు" },
];

export default function LanguageSelector({
  value,
  onChange,
  disabled = false,
}: LanguageSelectorProps) {
  return (
    <div className="flex items-center gap-1" role="group" aria-label="Select language">
      {LANGUAGE_OPTIONS.map((option) => (
        <button
          key={option.code}
          type="button"
          onClick={() => onChange(option.code)}
          disabled={disabled}
          aria-pressed={value === option.code}
          className={`rounded-full px-3 py-1 text-xs font-medium transition
            ${
              value === option.code
                ? "bg-emerald-700 text-white"
                : "border border-slate-300 bg-white text-slate-700 hover:border-emerald-600 hover:text-emerald-700"
            }
            disabled:cursor-not-allowed disabled:opacity-60`}
        >
          {option.label}
        </button>
      ))}
    </div>
  );
}
