import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import axios from "axios";
import { listSavedSchemes, unsaveScheme } from "../../services/savedSchemeService";
import type { SavedScheme } from "../../types/savedScheme";

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString("en-IN", { dateStyle: "medium" });
}

export default function FarmerSavedSchemesPage() {
  const [savedSchemes, setSavedSchemes] = useState<SavedScheme[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [removingIds, setRemovingIds] = useState<Set<number>>(new Set());

  const load = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const data = await listSavedSchemes();
      setSavedSchemes(data.saved_schemes);
    } catch (err) {
      if (axios.isAxiosError(err)) {
        setError(err.response?.data?.detail ?? "Failed to load saved schemes.");
      } else {
        setError("Failed to load saved schemes.");
      }
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  async function handleUnsave(schemeId: number) {
    setRemovingIds((prev) => new Set(prev).add(schemeId));
    try {
      await unsaveScheme(schemeId);
      setSavedSchemes((prev) =>
        prev.filter((s) => s.scheme_id !== schemeId),
      );
    } catch {
      // non-fatal — reload to sync
      await load();
    } finally {
      setRemovingIds((prev) => {
        const next = new Set(prev);
        next.delete(schemeId);
        return next;
      });
    }
  }

  return (
    <div className="mx-auto max-w-4xl px-4 py-10">
      <div className="mb-6">
        <p className="text-sm font-medium uppercase tracking-wide text-emerald-700">
          My Schemes
        </p>
        <h1 className="text-2xl font-bold text-slate-900">Saved Schemes</h1>
        <p className="mt-1 text-sm text-slate-500">
          Schemes you have bookmarked for quick access.
        </p>
      </div>

      {isLoading && (
        <p className="py-8 text-center text-sm text-slate-500">Loading saved schemes…</p>
      )}

      {error && (
        <p className="rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700" role="alert">
          {error}
        </p>
      )}

      {!isLoading && !error && savedSchemes.length === 0 && (
        <div className="rounded-xl border border-slate-200 bg-white p-8 text-center shadow-sm">
          <p className="text-slate-500">No saved schemes yet.</p>
          <Link
            to="/schemes"
            className="mt-3 inline-block rounded-lg bg-emerald-700 px-4 py-2 text-sm font-medium text-white hover:bg-emerald-800"
          >
            Browse schemes
          </Link>
        </div>
      )}

      {!isLoading && !error && savedSchemes.length > 0 && (
        <div className="space-y-4">
          {savedSchemes.map((saved) => {
            const isRemoving = removingIds.has(saved.scheme_id);
            return (
              <div
                key={saved.id}
                className="flex flex-wrap items-start justify-between gap-3 rounded-xl border border-slate-200 bg-white p-5 shadow-sm"
              >
                <div className="min-w-0 flex-1">
                  <h2 className="font-semibold text-slate-900">{saved.scheme.name}</h2>
                  <p className="mt-0.5 text-sm text-slate-600">
                    {saved.scheme.short_description}
                  </p>
                  <div className="mt-1 flex flex-wrap gap-x-3 text-xs text-slate-400">
                    <span>{saved.scheme.department}</span>
                    <span>{saved.scheme.state}</span>
                    <span>Saved {formatDate(saved.saved_at)}</span>
                  </div>
                </div>
                <div className="flex shrink-0 items-center gap-2">
                  <Link
                    to={`/schemes/${saved.scheme_id}`}
                    className="rounded-lg border border-emerald-600 px-3 py-1.5 text-xs font-medium text-emerald-700 hover:bg-emerald-50"
                  >
                    Details
                  </Link>
                  <button
                    type="button"
                    onClick={() => handleUnsave(saved.scheme_id)}
                    disabled={isRemoving}
                    aria-label={`Remove ${saved.scheme.name} from saved`}
                    className="rounded-lg border border-slate-300 px-3 py-1.5 text-xs font-medium text-slate-600 hover:bg-slate-50 disabled:opacity-50"
                  >
                    {isRemoving ? "Removing…" : "Remove"}
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
