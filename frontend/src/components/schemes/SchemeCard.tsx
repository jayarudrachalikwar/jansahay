import { Link } from "react-router-dom";
import SaveButton from "./SaveButton";
import type { Scheme } from "../../types/scheme";

interface SchemeCardProps { scheme: Scheme }

export default function SchemeCard({ scheme }: SchemeCardProps) {
  const isNational = scheme.state.toLowerCase().includes("all india") ||
    scheme.state.toLowerCase().includes("pan india") ||
    scheme.state.toLowerCase().includes("national");

  return (
    <article className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm transition hover:shadow-md sm:p-6">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-2 mb-1">
            <span className="rounded-full bg-emerald-100 px-2.5 py-0.5 text-xs font-medium text-emerald-800">
              {scheme.scheme_type}
            </span>
            <span className={`rounded-full px-2.5 py-0.5 text-xs font-medium ${
              isNational ? "bg-blue-100 text-blue-800" : "bg-slate-100 text-slate-700"
            }`}>
              {scheme.state}
            </span>
          </div>
          <h2 className="text-base font-semibold text-slate-900 leading-snug">{scheme.name}</h2>
          <p className="mt-0.5 text-xs text-slate-500">{scheme.department}</p>
        </div>
      </div>

      <p className="mt-3 text-sm text-slate-600 leading-relaxed">{scheme.short_description}</p>

      <div className="mt-3 rounded-lg bg-slate-50 px-3 py-2 text-sm">
        <span className="font-medium text-slate-600">Benefits: </span>
        <span className="text-slate-700">{scheme.benefits}</span>
      </div>

      <div className="mt-4 flex flex-wrap items-center gap-3">
        <Link
          to={`/schemes/${scheme.id}`}
          className="rounded-lg bg-emerald-700 px-4 py-2 text-xs font-semibold text-white transition hover:bg-emerald-800"
        >
          View Details & Eligibility
        </Link>
        <SaveButton schemeId={scheme.id} />
      </div>
    </article>
  );
}
