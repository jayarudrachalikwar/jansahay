import { FormEvent, useEffect, useState } from "react";
import axios from "axios";
import SchemeCard from "../../components/schemes/SchemeCard";
import { listSchemes } from "../../services/schemeService";
import type { Scheme } from "../../types/scheme";

function getErrorMessage(error: unknown) {
  if (axios.isAxiosError(error)) {
    const d = error.response?.data?.detail;
    if (typeof d === "string") return d;
  }
  return "Unable to load schemes. Please try again.";
}

export default function SchemesPage() {
  const [schemes, setSchemes] = useState<Scheme[]>([]);
  const [search, setSearch] = useState("");
  const [state, setState] = useState("");
  const [schemeType, setSchemeType] = useState("");
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function load() {
      setIsLoading(true);
      setError(null);
      try {
        const result = await listSchemes({
          search: search || undefined,
          state: state || undefined,
          scheme_type: schemeType || undefined,
        });
        setSchemes(result.schemes);
      } catch (e) {
        setError(getErrorMessage(e));
        setSchemes([]);
      } finally {
        setIsLoading(false);
      }
    }
    load();
  }, [search, state, schemeType]);

  return (
    <div className="mx-auto max-w-5xl px-4 py-10">
      {/* Page header */}
      <div className="mb-6">
        <p className="text-xs font-semibold uppercase tracking-widest text-emerald-700">Discover</p>
        <h1 className="mt-1 text-2xl font-bold text-slate-900">Government Welfare Schemes</h1>
        <p className="mt-1 text-sm text-slate-500">
          Search and filter schemes to explore eligibility and benefits.
        </p>
      </div>

      {/* Filter bar */}
      <form onSubmit={(e: FormEvent) => e.preventDefault()}
        className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm mb-6">
        <div className="grid gap-3 sm:grid-cols-3">
          <div>
            <label htmlFor="search" className="block text-xs font-medium text-slate-600 mb-1">Search</label>
            <input
              id="search" type="search" value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Name, department, benefits…"
              className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm outline-none transition focus:border-emerald-500 focus:ring-2 focus:ring-emerald-500/20"
            />
          </div>
          <div>
            <label htmlFor="state-filter" className="block text-xs font-medium text-slate-600 mb-1">State</label>
            <input
              id="state-filter" type="text" value={state}
              onChange={(e) => setState(e.target.value)}
              placeholder="e.g. Telangana, All India"
              className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm outline-none transition focus:border-emerald-500 focus:ring-2 focus:ring-emerald-500/20"
            />
          </div>
          <div>
            <label htmlFor="scheme-type-filter" className="block text-xs font-medium text-slate-600 mb-1">Scheme Type</label>
            <input
              id="scheme-type-filter" type="text" value={schemeType}
              onChange={(e) => setSchemeType(e.target.value)}
              placeholder="e.g. Crop Insurance, Financial…"
              className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm outline-none transition focus:border-emerald-500 focus:ring-2 focus:ring-emerald-500/20"
            />
          </div>
        </div>
        {(search || state || schemeType) && (
          <button type="button" onClick={() => { setSearch(""); setState(""); setSchemeType(""); }}
            className="mt-3 text-xs font-medium text-slate-500 hover:text-rose-600 transition">
            ✕ Clear filters
          </button>
        )}
      </form>

      {/* Results */}
      {isLoading && (
        <p className="py-12 text-center text-sm text-slate-500">Loading schemes…</p>
      )}
      {!isLoading && error && (
        <div className="rounded-xl border border-rose-200 bg-rose-50 px-4 py-4 text-sm text-rose-700">{error}</div>
      )}
      {!isLoading && !error && schemes.length === 0 && (
        <div className="rounded-xl border border-dashed border-slate-300 bg-slate-50 py-16 text-center">
          <p className="text-sm text-slate-500">No schemes match your filters.</p>
          <button type="button" onClick={() => { setSearch(""); setState(""); setSchemeType(""); }}
            className="mt-3 text-sm font-medium text-emerald-700 hover:underline">
            Clear filters
          </button>
        </div>
      )}
      {!isLoading && !error && schemes.length > 0 && (
        <>
          <p className="mb-4 text-xs text-slate-500">{schemes.length} scheme{schemes.length !== 1 ? "s" : ""} found</p>
          <div className="grid gap-5">
            {schemes.map((scheme) => <SchemeCard key={scheme.id} scheme={scheme} />)}
          </div>
        </>
      )}
    </div>
  );
}
