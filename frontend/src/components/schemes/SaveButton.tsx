import { useState } from "react";
import axios from "axios";
import { saveScheme, unsaveScheme } from "../../services/savedSchemeService";

interface SaveButtonProps {
  schemeId: number;
  initialSaved?: boolean;
  onToggle?: (saved: boolean) => void;
  className?: string;
}

export default function SaveButton({
  schemeId,
  initialSaved = false,
  onToggle,
  className = "",
}: SaveButtonProps) {
  const [saved, setSaved] = useState(initialSaved);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleClick() {
    setIsLoading(true);
    setError(null);
    try {
      if (saved) {
        await unsaveScheme(schemeId);
        setSaved(false);
        onToggle?.(false);
      } else {
        await saveScheme(schemeId);
        setSaved(true);
        onToggle?.(true);
      }
    } catch (err) {
      if (axios.isAxiosError(err)) {
        setError(err.response?.data?.detail ?? "Could not update saved status.");
      } else {
        setError("Could not update saved status.");
      }
    } finally {
      setIsLoading(false);
    }
  }

  return (
    <div className={`inline-flex flex-col items-start gap-1 ${className}`}>
      <button
        type="button"
        onClick={handleClick}
        disabled={isLoading}
        aria-pressed={saved}
        aria-label={saved ? "Unsave scheme" : "Save scheme"}
        className={`inline-flex items-center gap-1.5 rounded-lg border px-3 py-1.5 text-xs font-medium transition disabled:cursor-not-allowed disabled:opacity-50 ${
          saved
            ? "border-emerald-600 bg-emerald-50 text-emerald-700 hover:bg-white"
            : "border-slate-300 bg-white text-slate-600 hover:bg-slate-50"
        }`}
      >
        <span aria-hidden="true">{saved ? "★" : "☆"}</span>
        {isLoading ? "…" : saved ? "Saved" : "Save"}
      </button>
      {error && (
        <p className="text-xs text-red-600" role="alert">
          {error}
        </p>
      )}
    </div>
  );
}
