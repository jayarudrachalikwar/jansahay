import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import axios from "axios";
import {
  createApplication,
  getApplication,
  getApplicationChecklist,
  updateApplication,
} from "../../services/applicationService";
import { getScheme } from "../../services/schemeService";
import type {
  ApplicationChecklist,
  ApplicationStatus,
  FarmerSchemeApplication,
} from "../../types/application";
import type { SchemeDetail } from "../../types/scheme";

// ---------------------------------------------------------------------------
// Status display helpers
// ---------------------------------------------------------------------------

const STATUS_LABELS: Record<ApplicationStatus, string> = {
  not_started: "Not Started",
  preparing: "Preparing",
  ready_to_apply: "Ready to Apply",
  submitted: "Submitted",
};

const STATUS_STYLES: Record<ApplicationStatus, string> = {
  not_started: "bg-slate-100 text-slate-600",
  preparing: "bg-amber-100 text-amber-800",
  ready_to_apply: "bg-emerald-100 text-emerald-800",
  submitted: "bg-blue-100 text-blue-800",
};

const CHECKLIST_ICONS: Record<string, string> = {
  complete: "✓",
  missing: "○",
  attention: "⚠",
};

const CHECKLIST_STYLES: Record<string, string> = {
  complete: "text-emerald-600",
  missing: "text-rose-500",
  attention: "text-amber-600",
};

// ---------------------------------------------------------------------------
// Page
// ---------------------------------------------------------------------------

export default function FarmerApplicationPage() {
  const { schemeId: schemeIdStr } = useParams<{ schemeId: string }>();
  const schemeId = Number(schemeIdStr);

  const [scheme, setScheme] = useState<SchemeDetail | null>(null);
  const [application, setApplication] = useState<FarmerSchemeApplication | null>(null);
  const [checklist, setChecklist] = useState<ApplicationChecklist | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [saveError, setSaveError] = useState<string | null>(null);
  const [notes, setNotes] = useState("");
  const [selectedStatus, setSelectedStatus] = useState<ApplicationStatus>("preparing");

  useEffect(() => {
    if (!Number.isFinite(schemeId)) {
      setError("Invalid scheme ID.");
      setIsLoading(false);
      return;
    }

    async function load() {
      try {
        const [schemeData, checklistData] = await Promise.all([
          getScheme(schemeId),
          getApplicationChecklist(schemeId),
        ]);
        setScheme(schemeData);
        setChecklist(checklistData);

        try {
          const appData = await getApplication(schemeId);
          setApplication(appData);
          setSelectedStatus(appData.status);
          setNotes(appData.notes ?? "");
        } catch (appErr) {
          if (axios.isAxiosError(appErr) && appErr.response?.status === 404) {
            // No application yet — create one now with default status
            const created = await createApplication(schemeId);
            setApplication(created);
            setSelectedStatus(created.status);
            setNotes(created.notes ?? "");
          } else {
            throw appErr;
          }
        }
      } catch (err) {
        if (axios.isAxiosError(err)) {
          setError(err.response?.data?.detail ?? "Unable to load application details.");
        } else {
          setError("Unable to load application details.");
        }
      } finally {
        setIsLoading(false);
      }
    }

    load();
  }, [schemeId]);

  async function handleSave() {
    if (!application) return;
    setIsSaving(true);
    setSaveError(null);
    try {
      const updated = await updateApplication(schemeId, {
        status: selectedStatus,
        notes: notes.trim() || null,
      });
      setApplication(updated);
    } catch (err) {
      if (axios.isAxiosError(err)) {
        setSaveError(err.response?.data?.detail ?? "Failed to save.");
      } else {
        setSaveError("Failed to save.");
      }
    } finally {
      setIsSaving(false);
    }
  }

  if (isLoading) {
    return (
      <div className="mx-auto max-w-3xl px-4 py-12 text-center text-slate-600">
        Loading application…
      </div>
    );
  }

  if (error || !scheme) {
    return (
      <div className="mx-auto max-w-3xl px-4 py-12">
        <div className="rounded-xl border border-rose-200 bg-rose-50 p-6 text-sm text-rose-700">
          {error ?? "Unable to load this application."}
        </div>
        <Link to="/farmer/applications" className="mt-4 inline-block text-sm font-medium text-emerald-700">
          Back to applications
        </Link>
      </div>
    );
  }

  const completedCount = checklist?.completed ?? 0;
  const totalCount = checklist?.total ?? 0;
  const readinessPercent = totalCount > 0 ? Math.round((completedCount / totalCount) * 100) : 0;

  return (
    <div className="mx-auto max-w-3xl px-4 py-10 space-y-6">
      {/* Back link */}
      <Link
        to="/farmer/applications"
        className="text-sm font-medium text-emerald-700 hover:text-emerald-800"
      >
        ← Back to applications
      </Link>

      {/* 1. Scheme summary */}
      <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
        <p className="text-xs font-medium uppercase tracking-wide text-emerald-700">
          {scheme.scheme_type}
        </p>
        <h1 className="mt-1 text-xl font-bold text-slate-900">{scheme.name}</h1>
        <p className="mt-1 text-sm text-slate-500">{scheme.department} · {scheme.state}</p>
        <p className="mt-3 text-sm text-slate-700">{scheme.short_description}</p>
      </section>

      {/* 2 & 3. Status + readiness */}
      <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
        <h2 className="text-base font-semibold text-slate-900">Application Status</h2>
        {application && (
          <span className={`mt-2 inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${STATUS_STYLES[application.status]}`}>
            {STATUS_LABELS[application.status]}
          </span>
        )}
        {checklist && (
          <div className="mt-4">
            <div className="flex items-center justify-between text-sm">
              <span className="text-slate-600">Application readiness</span>
              <span className="font-medium text-emerald-700">{readinessPercent}%</span>
            </div>
            <div className="mt-1.5 h-2 overflow-hidden rounded-full bg-slate-100">
              <div
                className="h-full rounded-full bg-emerald-500 transition-all"
                style={{ width: `${readinessPercent}%` }}
                role="progressbar"
                aria-valuenow={readinessPercent}
                aria-valuemin={0}
                aria-valuemax={100}
              />
            </div>
            <p className="mt-1 text-xs text-slate-500">
              {completedCount} of {totalCount} items complete
              {checklist.ready && (
                <span className="ml-2 font-medium text-emerald-600">· Ready to apply</span>
              )}
            </p>
          </div>
        )}
      </section>

      {/* 4. Checklist */}
      {checklist && checklist.items.length > 0 && (
        <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
          <h2 className="text-base font-semibold text-slate-900">Application Checklist</h2>
          <ul className="mt-4 divide-y divide-slate-100">
            {checklist.items.map((item) => (
              <li key={item.key} className="flex items-start gap-3 py-2.5">
                <span className={`mt-0.5 shrink-0 font-semibold ${CHECKLIST_STYLES[item.status]}`}>
                  {CHECKLIST_ICONS[item.status]}
                </span>
                <div className="min-w-0">
                  <p className="text-sm font-medium text-slate-800">{item.label}</p>
                  <p className="text-xs text-slate-500">{item.message}</p>
                </div>
              </li>
            ))}
          </ul>
        </section>
      )}

      {/* 5. Missing profile info nudge */}
      {checklist && checklist.missing > 0 && (
        <div className="rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800">
          <p className="font-medium">
            {checklist.missing} item{checklist.missing !== 1 ? "s" : ""} still need{checklist.missing === 1 ? "s" : ""} attention.
          </p>
          <Link to="/profile" className="mt-1 inline-block text-xs font-medium text-amber-900 underline">
            Update your profile
          </Link>
        </div>
      )}

      {/* 6. Application process */}
      <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
        <h2 className="text-base font-semibold text-slate-900">How to Apply</h2>
        <p className="mt-2 text-sm text-slate-700 whitespace-pre-line">{scheme.application_process}</p>
      </section>

      {/* 7. Official website */}
      {scheme.official_website && (
        <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
          <h2 className="text-base font-semibold text-slate-900">Official Website</h2>
          <a
            href={scheme.official_website}
            target="_blank"
            rel="noreferrer"
            className="mt-2 inline-block text-sm text-emerald-700 hover:underline"
          >
            {scheme.official_website}
          </a>
          <p className="mt-1 text-xs text-slate-400">
            Development sample URL — not an official government integration.
          </p>
        </section>
      )}

      {/* 8 & 9. Status selector + notes */}
      <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
        <h2 className="text-base font-semibold text-slate-900">Update Application</h2>

        <div className="mt-4 flex flex-col gap-1">
          <label htmlFor="app_status" className="text-xs font-medium text-slate-600">
            Status
          </label>
          <select
            id="app_status"
            value={selectedStatus}
            onChange={(e) => setSelectedStatus(e.target.value as ApplicationStatus)}
            className="rounded-lg border border-slate-300 px-3 py-2 text-sm text-slate-700 focus:border-emerald-500 focus:outline-none"
          >
            <option value="not_started">Not Started</option>
            <option value="preparing">Preparing</option>
            <option value="ready_to_apply">Ready to Apply</option>
            <option value="submitted">Submitted (external)</option>
          </select>
        </div>

        <div className="mt-4 flex flex-col gap-1">
          <label htmlFor="app_notes" className="text-xs font-medium text-slate-600">
            Notes (optional)
          </label>
          <textarea
            id="app_notes"
            rows={3}
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            placeholder="Add any personal notes about your application…"
            className="rounded-lg border border-slate-300 px-3 py-2 text-sm text-slate-700 focus:border-emerald-500 focus:outline-none"
          />
        </div>

        {saveError && (
          <p className="mt-2 text-xs text-rose-600">{saveError}</p>
        )}

        <button
          type="button"
          onClick={handleSave}
          disabled={isSaving}
          className="mt-4 rounded-lg bg-emerald-700 px-4 py-2 text-sm font-medium text-white hover:bg-emerald-800 disabled:opacity-60"
        >
          {isSaving ? "Saving…" : "Save"}
        </button>
      </section>

      {/* 10. Disclaimer */}
      <div className="rounded-xl border border-slate-200 bg-slate-50 px-4 py-3 text-xs text-slate-500">
        <p className="font-medium text-slate-600">Important Disclaimer</p>
        <p className="mt-1">
          "Submitted" means you have indicated that you submitted the application through the
          official government channel. JanSahay AI does not submit applications to any government
          department on your behalf and cannot verify government submission status.
        </p>
      </div>
    </div>
  );
}
