import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import axios from "axios";
import RecommendationCard from "../../components/schemes/RecommendationCard";
import { getRecommendations } from "../../services/recommendationService";
import { getProfileCompletionDetail } from "../../services/profileService";
import type { SchemeRecommendation } from "../../types/scheme";
import type { ProfileCompletionDetail } from "../../types/profile";

// ---------------------------------------------------------------------------
// Types for filter/sort state
// ---------------------------------------------------------------------------

type SortBy = "score" | "name" | "eligibility";

interface Filters {
  eligible_only: boolean;
  sort_by: SortBy;
  scheme_type: string;
  state: string;
}

const DEFAULT_FILTERS: Filters = {
  eligible_only: false,
  sort_by: "score",
  scheme_type: "",
  state: "",
};

// ---------------------------------------------------------------------------
// Profile nudge
// ---------------------------------------------------------------------------

function ProfileNudge({ detail }: { detail: ProfileCompletionDetail }) {
  if (detail.completion_percentage >= 100) return null;
  const topMissing = detail.missing_fields.slice(0, 3);
  return (
    <div className="mb-5 rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800">
      <p className="font-medium">
        Your profile is {detail.completion_percentage}% complete — filling in more fields
        improves your recommendations.
      </p>
      {topMissing.length > 0 && (
        <p className="mt-1 text-xs text-amber-700">
          Missing: {topMissing.map((f) => f.label).join(", ")}.
        </p>
      )}
      <Link
        to="/profile"
        className="mt-2 inline-block text-xs font-medium text-amber-900 underline"
      >
        Update your profile
      </Link>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Page
// ---------------------------------------------------------------------------

export default function FarmerRecommendationsPage() {
  const [recommendations, setRecommendations] = useState<SchemeRecommendation[]>([]);
  const [profileDetail, setProfileDetail] = useState<ProfileCompletionDetail | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filters, setFilters] = useState<Filters>(DEFAULT_FILTERS);

  // Load profile completion detail silently (non-blocking)
  useEffect(() => {
    getProfileCompletionDetail()
      .then(setProfileDetail)
      .catch(() => {
        /* non-fatal — nudge simply won't show */
      });
  }, []);

  // Reload recommendations whenever filters change
  useEffect(() => {
    setIsLoading(true);
    setError(null);

    getRecommendations(50, {
      sort_by: filters.sort_by,
      eligible_only: filters.eligible_only,
      scheme_type: filters.scheme_type || undefined,
      state: filters.state || undefined,
    })
      .then((data) => setRecommendations(data.recommendations))
      .catch((err) => {
        if (axios.isAxiosError(err)) {
          setError(err.response?.data?.detail ?? "Unable to load recommendations.");
        } else {
          setError("Unable to load recommendations.");
        }
      })
      .finally(() => setIsLoading(false));
  }, [filters]);

  function setFilter<K extends keyof Filters>(key: K, value: Filters[K]) {
    setFilters((prev) => ({ ...prev, [key]: value }));
  }

  function clearFilters() {
    setFilters(DEFAULT_FILTERS);
  }

  const hasActiveFilters =
    filters.eligible_only ||
    filters.sort_by !== "score" ||
    filters.scheme_type !== "" ||
    filters.state !== "";

  return (
    <div className="mx-auto max-w-4xl px-4 py-10">
      {/* Page header */}
      <div className="mb-5">
        <p className="text-sm font-medium uppercase tracking-wide text-emerald-700">
          Personalized
        </p>
        <h1 className="text-2xl font-bold text-slate-900">Scheme Recommendations</h1>
        <p className="mt-1 text-sm text-slate-500">
          Ranked by how well your profile matches each scheme.
        </p>
      </div>

      {/* Profile nudge */}
      {profileDetail && <ProfileNudge detail={profileDetail} />}

      {/* Filter bar */}
      <div className="mb-5 flex flex-wrap items-end gap-3 rounded-xl border border-slate-200 bg-white px-4 py-3 shadow-sm">
        {/* Sort by */}
        <div className="flex flex-col gap-1">
          <label htmlFor="sort_by" className="text-xs font-medium text-slate-600">
            Sort by
          </label>
          <select
            id="sort_by"
            value={filters.sort_by}
            onChange={(e) => setFilter("sort_by", e.target.value as SortBy)}
            className="rounded-lg border border-slate-300 px-2 py-1.5 text-sm text-slate-700 focus:border-emerald-500 focus:outline-none"
          >
            <option value="score">Relevance</option>
            <option value="name">Name</option>
            <option value="eligibility">Eligibility</option>
          </select>
        </div>

        {/* Eligible only */}
        <div className="flex flex-col gap-1">
          <label htmlFor="eligible_only" className="text-xs font-medium text-slate-600">
            Eligibility
          </label>
          <select
            id="eligible_only"
            value={filters.eligible_only ? "true" : "false"}
            onChange={(e) => setFilter("eligible_only", e.target.value === "true")}
            className="rounded-lg border border-slate-300 px-2 py-1.5 text-sm text-slate-700 focus:border-emerald-500 focus:outline-none"
          >
            <option value="false">All schemes</option>
            <option value="true">Eligible only</option>
          </select>
        </div>

        {/* Scheme type */}
        <div className="flex flex-col gap-1">
          <label htmlFor="scheme_type" className="text-xs font-medium text-slate-600">
            Scheme type
          </label>
          <input
            id="scheme_type"
            type="text"
            placeholder="e.g. Insurance"
            value={filters.scheme_type}
            onChange={(e) => setFilter("scheme_type", e.target.value)}
            className="w-32 rounded-lg border border-slate-300 px-2 py-1.5 text-sm text-slate-700 focus:border-emerald-500 focus:outline-none"
          />
        </div>

        {/* State */}
        <div className="flex flex-col gap-1">
          <label htmlFor="rec_state" className="text-xs font-medium text-slate-600">
            State
          </label>
          <input
            id="rec_state"
            type="text"
            placeholder="e.g. Telangana"
            value={filters.state}
            onChange={(e) => setFilter("state", e.target.value)}
            className="w-32 rounded-lg border border-slate-300 px-2 py-1.5 text-sm text-slate-700 focus:border-emerald-500 focus:outline-none"
          />
        </div>

        {hasActiveFilters && (
          <button
            type="button"
            onClick={clearFilters}
            className="self-end rounded-lg border border-slate-300 px-3 py-1.5 text-xs font-medium text-slate-600 hover:bg-slate-50"
          >
            Clear
          </button>
        )}
      </div>

      {/* Results */}
      {isLoading && (
        <p className="py-8 text-center text-sm text-slate-500">
          Loading recommendations…
        </p>
      )}

      {error && (
        <div
          className="rounded-xl border border-rose-200 bg-rose-50 px-4 py-4 text-sm text-rose-700"
          role="alert"
        >
          <p className="font-medium">Could not load recommendations</p>
          <p className="mt-1">{error}</p>
          {error.toLowerCase().includes("profile") && (
            <Link to="/profile" className="mt-2 inline-block underline">
              Complete your profile
            </Link>
          )}
        </div>
      )}

      {!isLoading && !error && recommendations.length === 0 && (
        <div className="rounded-xl border border-slate-200 bg-white p-8 text-center shadow-sm">
          <p className="text-slate-500">
            {hasActiveFilters
              ? "No recommendations match the current filters."
              : "No recommendations available yet."}
          </p>
          {!hasActiveFilters && (
            <Link
              to="/profile"
              className="mt-3 inline-block rounded-lg bg-emerald-700 px-4 py-2 text-sm font-medium text-white hover:bg-emerald-800"
            >
              Complete your profile
            </Link>
          )}
          {hasActiveFilters && (
            <button
              type="button"
              onClick={clearFilters}
              className="mt-3 rounded-lg border border-slate-300 px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50"
            >
              Clear filters
            </button>
          )}
        </div>
      )}

      {!isLoading && !error && recommendations.length > 0 && (
        <div className="space-y-4">
          <p className="text-xs text-slate-500">
            {recommendations.length} scheme{recommendations.length !== 1 ? "s" : ""} found
          </p>
          {recommendations.map((rec) => (
            <RecommendationCard key={rec.scheme.id} recommendation={rec} />
          ))}
        </div>
      )}
    </div>
  );
}
