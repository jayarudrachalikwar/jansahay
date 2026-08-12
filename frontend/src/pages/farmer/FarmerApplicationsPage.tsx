import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import axios from "axios";
import { getApplications } from "../../services/applicationService";
import type { ApplicationStatus, FarmerSchemeApplication } from "../../types/application";

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

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString("en-IN", { dateStyle: "medium" });
}

export default function FarmerApplicationsPage() {
  const [applications, setApplications] = useState<FarmerSchemeApplication[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getApplications()
      .then((data) => setApplications(data.applications))
      .catch((err) => {
        if (axios.isAxiosError(err)) {
          setError(err.response?.data?.detail ?? "Failed to load applications.");
        } else {
          setError("Failed to load applications.");
        }
      })
      .finally(() => setIsLoading(false));
  }, []);

  return (
    <div className="mx-auto max-w-4xl px-4 py-10">
      <div className="mb-6">
        <p className="text-sm font-medium uppercase tracking-wide text-emerald-700">
          My Applications
        </p>
        <h1 className="text-2xl font-bold text-slate-900">Application Preparation</h1>
        <p className="mt-1 text-sm text-slate-500">
          Track your progress preparing to apply for government schemes.
        </p>
      </div>

      {isLoading && (
        <p className="py-8 text-center text-sm text-slate-500">Loading applications…</p>
      )}

      {error && (
        <p className="rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700" role="alert">
          {error}
        </p>
      )}

      {!isLoading && !error && applications.length === 0 && (
        <div className="rounded-xl border border-slate-200 bg-white p-8 text-center shadow-sm">
          <p className="text-slate-500">No applications yet.</p>
          <Link
            to="/schemes"
            className="mt-3 inline-block rounded-lg bg-emerald-700 px-4 py-2 text-sm font-medium text-white hover:bg-emerald-800"
          >
            Browse schemes
          </Link>
        </div>
      )}

      {!isLoading && !error && applications.length > 0 && (
        <div className="space-y-4">
          {applications.map((app) => (
            <div
              key={app.id}
              className="flex flex-wrap items-start justify-between gap-3 rounded-xl border border-slate-200 bg-white p-5 shadow-sm"
            >
              <div className="min-w-0 flex-1">
                <div className="flex flex-wrap items-center gap-2">
                  <h2 className="font-semibold text-slate-900">{app.scheme.name}</h2>
                  <span className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${STATUS_STYLES[app.status]}`}>
                    {STATUS_LABELS[app.status]}
                  </span>
                </div>
                <p className="mt-0.5 text-sm text-slate-600">{app.scheme.short_description}</p>
                <div className="mt-1 flex flex-wrap gap-x-3 text-xs text-slate-400">
                  <span>{app.scheme.department}</span>
                  <span>{app.scheme.state}</span>
                  <span>Updated {formatDate(app.updated_at)}</span>
                </div>
                {app.notes && (
                  <p className="mt-1 text-xs italic text-slate-500">{app.notes}</p>
                )}
              </div>
              <div className="flex shrink-0 flex-wrap items-center gap-2">
                <Link
                  to={`/farmer/applications/${app.scheme_id}`}
                  className="rounded-lg bg-emerald-700 px-3 py-1.5 text-xs font-medium text-white hover:bg-emerald-800"
                >
                  Continue
                </Link>
                <Link
                  to={`/schemes/${app.scheme_id}`}
                  className="rounded-lg border border-slate-300 px-3 py-1.5 text-xs font-medium text-slate-600 hover:bg-slate-50"
                >
                  View Scheme
                </Link>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
