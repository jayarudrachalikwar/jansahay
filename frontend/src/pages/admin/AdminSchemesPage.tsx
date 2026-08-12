import { useCallback, useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import axios from "axios";
import {
  deleteAdminScheme,
  listAdminSchemes,
} from "../../services/adminSchemeService";
import type { AdminSchemeResponse } from "../../types/adminScheme";

// ---------------------------------------------------------------------------
// Delete confirmation dialog
// ---------------------------------------------------------------------------

function DeleteDialog({
  scheme,
  onConfirm,
  onCancel,
  isDeleting,
}: {
  scheme: AdminSchemeResponse;
  onConfirm: () => void;
  onCancel: () => void;
  isDeleting: boolean;
}) {
  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4"
      role="dialog"
      aria-modal="true"
      aria-labelledby="delete-dialog-title"
    >
      <div className="w-full max-w-md rounded-xl bg-white p-6 shadow-xl">
        <h3
          id="delete-dialog-title"
          className="mb-2 text-base font-semibold text-slate-900"
        >
          Delete scheme?
        </h3>
        <p className="mb-4 text-sm text-slate-700">
          <span className="font-medium">{scheme.name}</span> will be permanently
          deleted including all eligibility criteria. This cannot be undone.
        </p>
        <div className="flex justify-end gap-3">
          <button
            type="button"
            onClick={onCancel}
            disabled={isDeleting}
            className="rounded-lg border border-slate-300 px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50 disabled:opacity-50"
          >
            Cancel
          </button>
          <button
            type="button"
            onClick={onConfirm}
            disabled={isDeleting}
            className="rounded-lg bg-red-600 px-4 py-2 text-sm font-medium text-white hover:bg-red-700 disabled:opacity-50"
          >
            {isDeleting ? "Deleting…" : "Delete"}
          </button>
        </div>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Page
// ---------------------------------------------------------------------------

export default function AdminSchemesPage() {
  const navigate = useNavigate();
  const [schemes, setSchemes] = useState<AdminSchemeResponse[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [deleteTarget, setDeleteTarget] = useState<AdminSchemeResponse | null>(null);
  const [isDeleting, setIsDeleting] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const data = await listAdminSchemes();
      setSchemes(data.schemes);
    } catch (err) {
      setError(
        axios.isAxiosError(err)
          ? (err.response?.data?.detail ?? "Failed to load schemes.")
          : "Failed to load schemes."
      );
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  async function handleDelete() {
    if (!deleteTarget) return;
    setIsDeleting(true);
    setActionError(null);
    try {
      await deleteAdminScheme(deleteTarget.id);
      setSchemes((prev) => prev.filter((s) => s.id !== deleteTarget.id));
      setDeleteTarget(null);
    } catch (err) {
      setActionError(
        axios.isAxiosError(err)
          ? (err.response?.data?.detail ?? "Delete failed.")
          : "Delete failed."
      );
      setDeleteTarget(null);
    } finally {
      setIsDeleting(false);
    }
  }

  return (
    <>
      {deleteTarget && (
        <DeleteDialog
          scheme={deleteTarget}
          onConfirm={handleDelete}
          onCancel={() => setDeleteTarget(null)}
          isDeleting={isDeleting}
        />
      )}

      <div className="mx-auto max-w-5xl px-4 py-10">
        <div className="mb-6 flex items-start justify-between gap-4">
          <div>
            <p className="text-sm font-medium uppercase tracking-wide text-emerald-700">
              Admin
            </p>
            <h1 className="text-2xl font-bold text-slate-900">
              Scheme Management
            </h1>
            <p className="mt-1 text-sm text-slate-500">
              Create and manage government welfare schemes.
            </p>
          </div>
          <button
            type="button"
            onClick={() => navigate("/admin/schemes/new")}
            className="shrink-0 rounded-lg bg-emerald-700 px-4 py-2 text-sm font-medium text-white hover:bg-emerald-800"
          >
            + New Scheme
          </button>
        </div>

        {actionError && (
          <p className="mb-4 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700" role="alert">
            {actionError}
          </p>
        )}

        <div className="rounded-xl border border-slate-200 bg-white shadow-sm">
          <div className="border-b border-slate-100 px-6 py-4">
            <h2 className="text-base font-semibold text-slate-800">
              Schemes{" "}
              <span className="ml-1 text-sm font-normal text-slate-400">
                ({schemes.length})
              </span>
            </h2>
          </div>

          {isLoading && (
            <p className="px-6 py-8 text-center text-sm text-slate-500">
              Loading schemes…
            </p>
          )}

          {error && (
            <p className="px-6 py-4 text-sm text-red-600" role="alert">
              {error}
            </p>
          )}

          {!isLoading && !error && schemes.length === 0 && (
            <div className="px-6 py-8 text-center">
              <p className="text-sm text-slate-500">No schemes yet.</p>
              <button
                type="button"
                onClick={() => navigate("/admin/schemes/new")}
                className="mt-3 rounded-lg bg-emerald-700 px-4 py-2 text-sm font-medium text-white hover:bg-emerald-800"
              >
                Create first scheme
              </button>
            </div>
          )}

          {!isLoading && !error && schemes.length > 0 && (
            <div className="divide-y divide-slate-100">
              {schemes.map((scheme) => (
                <div
                  key={scheme.id}
                  className="flex flex-wrap items-start justify-between gap-4 px-6 py-5"
                >
                  <div className="min-w-0 flex-1">
                    <div className="flex flex-wrap items-center gap-2">
                      <p className="font-medium text-slate-900">{scheme.name}</p>
                      <span
                        className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ${
                          scheme.is_active
                            ? "bg-emerald-100 text-emerald-800"
                            : "bg-slate-100 text-slate-500"
                        }`}
                      >
                        {scheme.is_active ? "Active" : "Inactive"}
                      </span>
                    </div>
                    <p className="mt-0.5 text-sm text-slate-500">
                      {scheme.short_description}
                    </p>
                    <div className="mt-1 flex flex-wrap gap-x-3 text-xs text-slate-400">
                      <span>{scheme.department}</span>
                      <span>{scheme.state}</span>
                      <span>{scheme.scheme_type}</span>
                      <span>
                        {scheme.eligibility_criteria.length} criteria
                      </span>
                    </div>
                  </div>

                  <div className="flex shrink-0 items-center gap-2">
                    <button
                      type="button"
                      onClick={() => navigate(`/admin/schemes/${scheme.id}/edit`)}
                      className="rounded-lg border border-slate-300 px-3 py-1.5 text-xs font-medium text-slate-600 hover:bg-slate-50"
                      aria-label={`Edit ${scheme.name}`}
                    >
                      Edit
                    </button>
                    <button
                      type="button"
                      onClick={() => setDeleteTarget(scheme)}
                      className="rounded-lg border border-red-300 px-3 py-1.5 text-xs font-medium text-red-600 hover:bg-red-50"
                      aria-label={`Delete ${scheme.name}`}
                    >
                      Delete
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </>
  );
}
