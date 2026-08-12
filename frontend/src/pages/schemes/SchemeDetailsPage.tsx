import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import axios from "axios";
import EligibilityBadge from "../../components/schemes/EligibilityBadge";
import SaveButton from "../../components/schemes/SaveButton";
import { checkSchemeEligibility, getScheme } from "../../services/schemeService";
import { createApplication } from "../../services/applicationService";
import type { SchemeDetail, SchemeEligibilityResult } from "../../types/scheme";

function getErrorMessage(error: unknown, fallback: string): string {
  if (axios.isAxiosError(error)) {
    const detail = error.response?.data?.detail;
    if (typeof detail === "string") {
      return detail;
    }
  }
  return fallback;
}

export default function SchemeDetailsPage() {
  const { id } = useParams<{ id: string }>();
  const schemeId = Number(id);
  const navigate = useNavigate();

  const [scheme, setScheme] = useState<SchemeDetail | null>(null);
  const [eligibility, setEligibility] = useState<SchemeEligibilityResult | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isCheckingEligibility, setIsCheckingEligibility] = useState(false);
  const [isStartingApp, setIsStartingApp] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [eligibilityError, setEligibilityError] = useState<string | null>(null);

  useEffect(() => {
    if (!Number.isFinite(schemeId)) {
      setError("Invalid scheme ID.");
      setIsLoading(false);
      return;
    }

    async function loadScheme() {
      setIsLoading(true);
      setError(null);
      try {
        const result = await getScheme(schemeId);
        setScheme(result);
      } catch (loadError) {
        setError(getErrorMessage(loadError, "Unable to load scheme details."));
      } finally {
        setIsLoading(false);
      }
    }

    loadScheme();
  }, [schemeId]);

  async function handleCheckEligibility() {
    if (!Number.isFinite(schemeId)) {
      return;
    }

    setIsCheckingEligibility(true);
    setEligibilityError(null);
    setEligibility(null);

    try {
      const result = await checkSchemeEligibility(schemeId);
      setEligibility(result);
    } catch (checkError) {
      setEligibilityError(
        getErrorMessage(checkError, "Unable to check eligibility. Please try again."),
      );
    } finally {
      setIsCheckingEligibility(false);
    }
  }

  if (isLoading) {
    return (
      <div className="mx-auto max-w-4xl px-4 py-12 text-center text-slate-600">
        Loading scheme details...
      </div>
    );
  }

  if (error || !scheme) {
    return (
      <div className="mx-auto max-w-4xl px-4 py-12">
        <div className="rounded-xl border border-rose-200 bg-rose-50 p-6 text-sm text-rose-700">
          {error ?? "Scheme not found."}
        </div>
        <Link to="/schemes" className="mt-4 inline-block text-sm font-medium text-emerald-700">
          Back to schemes
        </Link>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-4xl px-4 py-12">
      <Link to="/schemes" className="text-sm font-medium text-emerald-700 hover:text-emerald-800">
        Back to schemes
      </Link>

      <section className="mt-4 rounded-2xl border border-slate-200 bg-white p-8 shadow-sm">
        <p className="text-xs font-medium uppercase tracking-wide text-emerald-700">
          {scheme.scheme_type}
        </p>
        <h1 className="mt-2 text-2xl font-bold text-slate-900">{scheme.name}</h1>
        <p className="mt-2 text-sm text-slate-600">{scheme.department} · {scheme.state}</p>

        <div className="mt-6 space-y-6 text-sm text-slate-700">
          <div>
            <h2 className="text-base font-semibold text-slate-900">Description</h2>
            <p className="mt-2">{scheme.detailed_description}</p>
          </div>
          <div>
            <h2 className="text-base font-semibold text-slate-900">Benefits</h2>
            <p className="mt-2">{scheme.benefits}</p>
          </div>
          <div>
            <h2 className="text-base font-semibold text-slate-900">Application Process</h2>
            <p className="mt-2">{scheme.application_process}</p>
          </div>
          {scheme.official_website && (
            <div>
              <h2 className="text-base font-semibold text-slate-900">Official Website</h2>
              <a
                href={scheme.official_website}
                target="_blank"
                rel="noreferrer"
                className="mt-2 inline-block text-emerald-700 hover:underline"
              >
                {scheme.official_website}
              </a>
              <p className="mt-1 text-xs text-slate-500">
                Development sample URL — not an official government integration.
              </p>
            </div>
          )}
          <div>
            <h2 className="text-base font-semibold text-slate-900">Eligibility Information</h2>
            {scheme.eligibility_criteria.length === 0 ? (
              <p className="mt-2">No specific eligibility criteria are listed for this scheme.</p>
            ) : (
              <ul className="mt-2 list-disc space-y-2 pl-5">
                {scheme.eligibility_criteria.map((criterion) => (
                  <li key={`${criterion.field_name}-${criterion.operator}-${criterion.expected_value}`}>
                    {criterion.description ??
                      `${criterion.field_name} ${criterion.operator} ${criterion.expected_value}`}
                  </li>
                ))}
              </ul>
            )}
          </div>
        </div>

        <div className="mt-8 flex flex-wrap items-center gap-3">
          <button
            type="button"
            onClick={handleCheckEligibility}
            disabled={isCheckingEligibility}
            className="rounded-lg bg-emerald-700 px-4 py-2 text-sm font-medium text-white transition hover:bg-emerald-800 disabled:cursor-not-allowed disabled:opacity-70"
          >
            {isCheckingEligibility ? "Checking eligibility..." : "Check Eligibility"}
          </button>
          <button
            type="button"
            disabled={isStartingApp}
            onClick={async () => {
              if (!Number.isFinite(schemeId)) return;
              setIsStartingApp(true);
              try {
                await createApplication(schemeId);
              } catch {
                // Already exists or other error — navigate anyway
              } finally {
                setIsStartingApp(false);
              }
              navigate(`/farmer/applications/${schemeId}`);
            }}
            className="rounded-lg border border-emerald-600 px-4 py-2 text-sm font-medium text-emerald-700 transition hover:bg-emerald-50 disabled:cursor-not-allowed disabled:opacity-70"
          >
            {isStartingApp ? "Starting…" : "Prepare Application"}
          </button>
          <SaveButton schemeId={schemeId} />
        </div>
      </section>

      {eligibilityError && (
        <section className="mt-6 rounded-xl border border-amber-200 bg-amber-50 p-5 text-sm text-amber-800">
          {eligibilityError}
        </section>
      )}

      {eligibility && (
        <section className="mt-6 rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
          <div className="flex flex-wrap items-center gap-3">
            <h2 className="text-lg font-semibold text-slate-900">Eligibility Result</h2>
            <EligibilityBadge eligible={eligibility.eligible} />
          </div>
          <ul className="mt-4 list-disc space-y-2 pl-5 text-sm text-slate-700">
            {eligibility.reasons.map((reason) => (
              <li key={reason}>{reason}</li>
            ))}
          </ul>
        </section>
      )}
    </div>
  );
}
