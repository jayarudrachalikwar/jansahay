import { Link, useNavigate } from "react-router-dom";
import SaveButton from "./SaveButton";
import { createApplication } from "../../services/applicationService";
import type { MatchStatus, SchemeRecommendation } from "../../types/scheme";

// ---------------------------------------------------------------------------
// Badges
// ---------------------------------------------------------------------------

const MATCH_STYLES: Record<MatchStatus, string> = {
  eligible: "bg-emerald-100 text-emerald-800",
  partial: "bg-yellow-100 text-yellow-800",
  no_match: "bg-slate-100 text-slate-600",
};

const MATCH_LABELS: Record<MatchStatus, string> = {
  eligible: "Eligible",
  partial: "Partial Match",
  no_match: "No Match",
};

function MatchStatusBadge({ status }: { status: MatchStatus }) {
  return (
    <span
      className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${MATCH_STYLES[status]}`}
    >
      {MATCH_LABELS[status]}
    </span>
  );
}

function ScoreBadge({ score }: { score: number }) {
  const color =
    score >= 70
      ? "bg-emerald-100 text-emerald-800"
      : score >= 40
        ? "bg-yellow-100 text-yellow-800"
        : "bg-slate-100 text-slate-600";
  return (
    <span
      className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${color}`}
    >
      {score}% match
    </span>
  );
}

// ---------------------------------------------------------------------------
// Card
// ---------------------------------------------------------------------------

interface RecommendationCardProps {
  recommendation: SchemeRecommendation;
}

export default function RecommendationCard({ recommendation }: RecommendationCardProps) {
  const { scheme, relevance_score, summary, factors, match_status } = recommendation;
  const navigate = useNavigate();

  async function handlePrepareApplication() {
    try {
      await createApplication(scheme.id);
    } catch {
      // Already exists — navigate anyway
    }
    navigate(`/farmer/applications/${scheme.id}`);
  }

  return (
    <article className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
      {/* Header row */}
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0 flex-1">
          <p className="text-xs font-medium uppercase tracking-wide text-emerald-700">
            Profile-based recommendation
          </p>
          <h3 className="mt-1 text-base font-semibold text-slate-900">{scheme.name}</h3>
        </div>
        <div className="flex shrink-0 flex-wrap items-center gap-2">
          <MatchStatusBadge status={match_status} />
          <ScoreBadge score={relevance_score} />
        </div>
      </div>

      {/* Short description */}
      <p className="mt-2 text-sm text-slate-600">{scheme.short_description}</p>

      {/* Factors — shown only if non-empty */}
      {factors.length > 0 && (
        <div className="mt-3">
          <p className="text-xs font-semibold text-slate-500">Why this scheme matches:</p>
          <ul className="mt-1 space-y-0.5">
            {factors.map((factor, idx) => (
              <li key={idx} className="flex items-start gap-1.5 text-xs text-slate-700">
                <span className="mt-0.5 text-emerald-600">✓</span>
                <span>{factor}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Summary (fallback when no factors) */}
      {factors.length === 0 && (
        <p className="mt-2 text-xs italic text-slate-500">{summary}</p>
      )}

      {/* Metadata row */}
      <div className="mt-2 flex flex-wrap gap-x-3 text-xs text-slate-400">
        <span>{scheme.department}</span>
        <span>{scheme.state}</span>
        <span>{scheme.scheme_type}</span>
      </div>

      {/* Actions */}
      <div className="mt-4 flex flex-wrap items-center gap-3">
        <SaveButton schemeId={scheme.id} />
        {match_status === "eligible" && (
          <button
            type="button"
            onClick={handlePrepareApplication}
            className="rounded-lg bg-emerald-700 px-3 py-1.5 text-xs font-medium text-white hover:bg-emerald-800"
          >
            Prepare Application
          </button>
        )}
        {match_status === "partial" && (
          <Link
            to="/profile"
            className="rounded-lg border border-amber-500 px-3 py-1.5 text-xs font-medium text-amber-700 hover:bg-amber-50"
          >
            Complete Profile
          </Link>
        )}
        {match_status === "no_match" && (
          <Link
            to={`/schemes/${scheme.id}`}
            className="rounded-lg border border-slate-300 px-3 py-1.5 text-xs font-medium text-slate-600 hover:bg-slate-50"
          >
            View Scheme
          </Link>
        )}
        {match_status !== "no_match" && (
          <Link
            to={`/schemes/${scheme.id}`}
            className="rounded-lg border border-emerald-600 px-3 py-1.5 text-xs font-medium text-emerald-700 hover:bg-emerald-50"
          >
            View Details
          </Link>
        )}
      </div>
    </article>
  );
}
