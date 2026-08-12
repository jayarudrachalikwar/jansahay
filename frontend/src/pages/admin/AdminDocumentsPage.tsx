import { useCallback, useEffect, useRef, useState } from "react";
import axios from "axios";
import type {
  DocumentChunkStats,
  DocumentStatus,
  GovernmentDocument,
  KnowledgeBaseStats,
} from "../../types/document";
import {
  deleteDocument,
  getDocumentChunks,
  getKnowledgeBaseStats,
  ingestDocument,
  listDocuments,
  updateDocumentStatus,
  uploadDocument,
} from "../../services/documentService";

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function formatDate(iso: string | null): string {
  if (!iso) return "—";
  return new Date(iso).toLocaleString("en-IN", {
    dateStyle: "medium",
    timeStyle: "short",
  });
}

// ---------------------------------------------------------------------------
// Status badge
// ---------------------------------------------------------------------------

const STATUS_STYLES: Record<DocumentStatus, string> = {
  uploaded: "bg-slate-100 text-slate-700",
  processing: "bg-yellow-100 text-yellow-800",
  indexed: "bg-emerald-100 text-emerald-800",
  failed: "bg-red-100 text-red-700",
  inactive: "bg-slate-100 text-slate-500",
};

function StatusBadge({ status }: { status: DocumentStatus }) {
  return (
    <span
      className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium capitalize ${STATUS_STYLES[status]}`}
    >
      {status}
    </span>
  );
}

// ---------------------------------------------------------------------------
// KB stats panel
// ---------------------------------------------------------------------------

function KbStatsPanel({ stats }: { stats: KnowledgeBaseStats | null }) {
  if (!stats) {
    return (
      <div className="mb-6 rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
        <p className="text-sm text-slate-400">Loading knowledge base stats…</p>
      </div>
    );
  }

  const statusOrder: DocumentStatus[] = [
    "indexed",
    "uploaded",
    "processing",
    "failed",
    "inactive",
  ];

  return (
    <div className="mb-6 rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
      <div className="mb-4 flex items-center justify-between">
        <h2 className="text-base font-semibold text-slate-800">
          Knowledge Base
        </h2>
        <span
          className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-xs font-medium ${
            stats.qdrant_reachable
              ? "bg-emerald-100 text-emerald-800"
              : "bg-red-100 text-red-700"
          }`}
        >
          <span
            className={`h-1.5 w-1.5 rounded-full ${stats.qdrant_reachable ? "bg-emerald-500" : "bg-red-500"}`}
          />
          {stats.qdrant_reachable ? "Qdrant connected" : "Qdrant unreachable"}
        </span>
      </div>

      <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
        <div className="rounded-lg bg-slate-50 p-3">
          <p className="text-xs text-slate-500">Total documents</p>
          <p className="mt-1 text-2xl font-bold text-slate-900">
            {stats.total_documents}
          </p>
        </div>
        <div className="rounded-lg bg-emerald-50 p-3">
          <p className="text-xs text-slate-500">Indexed chunks</p>
          <p className="mt-1 text-2xl font-bold text-emerald-800">
            {stats.total_indexed_chunks}
          </p>
        </div>
        {statusOrder.map((s) => {
          const count = stats.by_status[s] ?? 0;
          if (count === 0) return null;
          return (
            <div key={s} className="rounded-lg bg-slate-50 p-3">
              <p className="text-xs capitalize text-slate-500">{s}</p>
              <p className="mt-1 text-2xl font-bold text-slate-900">{count}</p>
            </div>
          );
        })}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Delete confirmation dialog
// ---------------------------------------------------------------------------

interface DeleteDialogProps {
  document: GovernmentDocument;
  onConfirm: () => void;
  onCancel: () => void;
  isDeleting: boolean;
}

function DeleteDialog({
  document,
  onConfirm,
  onCancel,
  isDeleting,
}: DeleteDialogProps) {
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
          Permanently delete document?
        </h3>
        <p className="mb-1 text-sm font-medium text-slate-700">
          {document.original_filename}
        </p>
        <p className="mb-4 text-sm text-slate-500">
          This will permanently remove the document from:
        </p>
        <ul className="mb-5 space-y-1 text-sm text-slate-600">
          <li className="flex items-start gap-2">
            <span className="mt-0.5 text-red-500">✕</span>
            The document database
          </li>
          <li className="flex items-start gap-2">
            <span className="mt-0.5 text-red-500">✕</span>
            Uploaded file storage
          </li>
          <li className="flex items-start gap-2">
            <span className="mt-0.5 text-red-500">✕</span>
            The RAG / Qdrant vector index
          </li>
        </ul>
        <p className="mb-5 text-xs text-red-600 font-medium">
          This action cannot be undone.
        </p>
        <div className="flex justify-end gap-3">
          <button
            type="button"
            onClick={onCancel}
            disabled={isDeleting}
            className="rounded-lg border border-slate-300 px-4 py-2 text-sm font-medium text-slate-700 transition hover:bg-slate-50 disabled:opacity-50"
          >
            Cancel
          </button>
          <button
            type="button"
            onClick={onConfirm}
            disabled={isDeleting}
            className="rounded-lg bg-red-600 px-4 py-2 text-sm font-medium text-white transition hover:bg-red-700 disabled:opacity-50"
          >
            {isDeleting ? "Deleting…" : "Delete permanently"}
          </button>
        </div>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Page
// ---------------------------------------------------------------------------

const ALL_STATUSES: Array<{ label: string; value: string }> = [
  { label: "All statuses", value: "" },
  { label: "Uploaded", value: "uploaded" },
  { label: "Processing", value: "processing" },
  { label: "Indexed", value: "indexed" },
  { label: "Failed", value: "failed" },
  { label: "Inactive", value: "inactive" },
];

export default function AdminDocumentsPage() {
  const [documents, setDocuments] = useState<GovernmentDocument[]>([]);
  const [kbStats, setKbStats] = useState<KnowledgeBaseStats | null>(null);
  const [chunkCounts, setChunkCounts] = useState<Record<number, DocumentChunkStats>>({});

  const [isLoading, setIsLoading] = useState(true);
  const [isUploading, setIsUploading] = useState(false);

  // Search / filter state
  const [searchInput, setSearchInput] = useState("");
  const [activeSearch, setActiveSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("");

  // Feedback
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [uploadSuccess, setUploadSuccess] = useState<string | null>(null);
  const [actionErrors, setActionErrors] = useState<Record<number, string>>({});
  const [busyIds, setBusyIds] = useState<Set<number>>(new Set());

  // Delete dialog
  const [deleteTarget, setDeleteTarget] = useState<GovernmentDocument | null>(null);
  const [isDeleting, setIsDeleting] = useState(false);

  const fileInputRef = useRef<HTMLInputElement>(null);

  // ---------------------------------------------------------------------------
  // Data loading
  // ---------------------------------------------------------------------------

  const loadDocuments = useCallback(async () => {
    setIsLoading(true);
    try {
      const result = await listDocuments({
        status: statusFilter || undefined,
        search: activeSearch || undefined,
      });
      setDocuments(result.documents);
    } catch {
      // list failure is non-fatal — show empty state
    } finally {
      setIsLoading(false);
    }
  }, [statusFilter, activeSearch]);

  const loadKbStats = useCallback(async () => {
    try {
      const stats = await getKnowledgeBaseStats();
      setKbStats(stats);
    } catch {
      // non-fatal
    }
  }, []);

  // Fetch chunk count for a single document without blocking the rest of the UI
  const loadChunkCount = useCallback(async (doc: GovernmentDocument) => {
    if (doc.status !== "indexed") return;
    try {
      const stats = await getDocumentChunks(doc.id);
      setChunkCounts((prev) => ({ ...prev, [doc.id]: stats }));
    } catch {
      // non-fatal — chunk count simply won't display
    }
  }, []);

  useEffect(() => {
    loadDocuments();
  }, [loadDocuments]);

  useEffect(() => {
    loadKbStats();
  }, [loadKbStats]);

  // Fetch chunk counts for indexed docs whenever the document list changes
  useEffect(() => {
    documents.forEach((doc) => {
      if (doc.status === "indexed" && !(doc.id in chunkCounts)) {
        loadChunkCount(doc);
      }
    });
    // intentionally not listing chunkCounts to avoid infinite loop
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [documents, loadChunkCount]);

  // ---------------------------------------------------------------------------
  // Helpers
  // ---------------------------------------------------------------------------

  function setDocumentBusy(id: number, busy: boolean) {
    setBusyIds((prev) => {
      const next = new Set(prev);
      busy ? next.add(id) : next.delete(id);
      return next;
    });
  }

  function setActionError(id: number, message: string | null) {
    setActionErrors((prev) => {
      const next = { ...prev };
      if (message === null) delete next[id];
      else next[id] = message;
      return next;
    });
  }

  function extractErrorDetail(err: unknown): string {
    if (axios.isAxiosError(err)) {
      return err.response?.data?.detail ?? "An error occurred.";
    }
    return "An error occurred.";
  }

  // ---------------------------------------------------------------------------
  // Search / filter handlers
  // ---------------------------------------------------------------------------

  function handleSearchSubmit(e: React.FormEvent) {
    e.preventDefault();
    setActiveSearch(searchInput.trim());
  }

  function handleSearchClear() {
    setSearchInput("");
    setActiveSearch("");
  }

  function handleStatusChange(e: React.ChangeEvent<HTMLSelectElement>) {
    setStatusFilter(e.target.value);
  }

  // ---------------------------------------------------------------------------
  // Upload
  // ---------------------------------------------------------------------------

  async function handleFileChange(event: React.ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    if (!file) return;

    setUploadError(null);
    setUploadSuccess(null);
    setIsUploading(true);

    try {
      const doc = await uploadDocument(file);
      setDocuments((prev) => [doc, ...prev]);
      setUploadSuccess(
        `"${doc.original_filename}" uploaded. Click Re-ingest to index it.`,
      );
      await loadKbStats();
    } catch (err) {
      setUploadError(extractErrorDetail(err));
    } finally {
      setIsUploading(false);
      if (fileInputRef.current) fileInputRef.current.value = "";
    }
  }

  // ---------------------------------------------------------------------------
  // Re-ingest
  // ---------------------------------------------------------------------------

  async function handleIngest(doc: GovernmentDocument) {
    setDocumentBusy(doc.id, true);
    setActionError(doc.id, null);
    try {
      const updated = await ingestDocument(doc.id);
      setDocuments((prev) => prev.map((d) => (d.id === updated.id ? updated : d)));
      // Refresh chunk count for the newly indexed doc
      await loadChunkCount(updated);
      await loadKbStats();
    } catch (err) {
      setActionError(doc.id, extractErrorDetail(err));
      await loadDocuments();
    } finally {
      setDocumentBusy(doc.id, false);
    }
  }

  // ---------------------------------------------------------------------------
  // Activate / deactivate
  // ---------------------------------------------------------------------------

  async function handleToggleActive(doc: GovernmentDocument) {
    setDocumentBusy(doc.id, true);
    setActionError(doc.id, null);
    try {
      const updated = await updateDocumentStatus(doc.id, {
        is_active: !doc.is_active,
      });
      setDocuments((prev) => prev.map((d) => (d.id === updated.id ? updated : d)));
    } catch (err) {
      setActionError(doc.id, extractErrorDetail(err));
    } finally {
      setDocumentBusy(doc.id, false);
    }
  }

  // ---------------------------------------------------------------------------
  // Delete
  // ---------------------------------------------------------------------------

  function handleDeleteClick(doc: GovernmentDocument) {
    setDeleteTarget(doc);
  }

  async function handleDeleteConfirm() {
    if (!deleteTarget) return;
    setIsDeleting(true);
    try {
      await deleteDocument(deleteTarget.id);
      setDocuments((prev) => prev.filter((d) => d.id !== deleteTarget.id));
      setChunkCounts((prev) => {
        const next = { ...prev };
        delete next[deleteTarget.id];
        return next;
      });
      setDeleteTarget(null);
      await loadKbStats();
    } catch (err) {
      setActionError(deleteTarget.id, extractErrorDetail(err));
      setDeleteTarget(null);
    } finally {
      setIsDeleting(false);
    }
  }

  function handleDeleteCancel() {
    setDeleteTarget(null);
  }

  // ---------------------------------------------------------------------------
  // Render
  // ---------------------------------------------------------------------------

  return (
    <>
      {/* Delete confirmation dialog */}
      {deleteTarget && (
        <DeleteDialog
          document={deleteTarget}
          onConfirm={handleDeleteConfirm}
          onCancel={handleDeleteCancel}
          isDeleting={isDeleting}
        />
      )}

      <div className="mx-auto max-w-5xl px-4 py-10">
        {/* Page header */}
        <div className="mb-6 flex flex-col gap-1">
          <p className="text-sm font-medium uppercase tracking-wide text-emerald-700">
            Admin
          </p>
          <h1 className="text-2xl font-bold text-slate-900">
            Knowledge Base Management
          </h1>
          <p className="text-sm text-slate-500">
            Upload and manage government scheme PDF documents for RAG retrieval.
          </p>
        </div>

        {/* KB stats */}
        <KbStatsPanel stats={kbStats} />

        {/* Upload area */}
        <div className="mb-6 rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
          <h2 className="mb-3 text-base font-semibold text-slate-800">
            Upload PDF Document
          </h2>
          <label className="flex cursor-pointer items-center gap-3">
            <span className="rounded-lg bg-emerald-700 px-4 py-2 text-sm font-medium text-white transition hover:bg-emerald-800">
              {isUploading ? "Uploading…" : "Choose PDF"}
            </span>
            <span className="text-sm text-slate-500">PDF only, max 20 MB</span>
            <input
              ref={fileInputRef}
              type="file"
              accept="application/pdf,.pdf"
              className="sr-only"
              disabled={isUploading}
              onChange={handleFileChange}
            />
          </label>
          {uploadSuccess && (
            <p className="mt-3 text-sm text-emerald-700" role="status">
              {uploadSuccess}
            </p>
          )}
          {uploadError && (
            <p className="mt-3 text-sm text-red-600" role="alert">
              {uploadError}
            </p>
          )}
        </div>

        {/* Search + filter bar */}
        <div className="mb-4 flex flex-wrap items-end gap-3">
          <form
            onSubmit={handleSearchSubmit}
            className="flex flex-1 items-center gap-2"
          >
            <input
              type="text"
              value={searchInput}
              onChange={(e) => setSearchInput(e.target.value)}
              placeholder="Search by filename…"
              className="flex-1 rounded-lg border border-slate-300 px-3 py-2 text-sm text-slate-900 placeholder-slate-400 focus:border-emerald-500 focus:outline-none focus:ring-1 focus:ring-emerald-500"
              aria-label="Search documents by filename"
            />
            <button
              type="submit"
              className="rounded-lg bg-emerald-700 px-3 py-2 text-sm font-medium text-white transition hover:bg-emerald-800"
            >
              Search
            </button>
            {(activeSearch || statusFilter) && (
              <button
                type="button"
                onClick={() => {
                  handleSearchClear();
                  setStatusFilter("");
                }}
                className="rounded-lg border border-slate-300 px-3 py-2 text-sm text-slate-600 transition hover:bg-slate-50"
              >
                Clear
              </button>
            )}
          </form>

          <select
            value={statusFilter}
            onChange={handleStatusChange}
            className="rounded-lg border border-slate-300 px-3 py-2 text-sm text-slate-700 focus:border-emerald-500 focus:outline-none focus:ring-1 focus:ring-emerald-500"
            aria-label="Filter by status"
          >
            {ALL_STATUSES.map((s) => (
              <option key={s.value} value={s.value}>
                {s.label}
              </option>
            ))}
          </select>
        </div>

        {/* Document table */}
        <div className="rounded-xl border border-slate-200 bg-white shadow-sm">
          <div className="border-b border-slate-100 px-6 py-4">
            <h2 className="text-base font-semibold text-slate-800">
              Documents{" "}
              <span className="ml-1 text-sm font-normal text-slate-400">
                ({documents.length})
              </span>
            </h2>
          </div>

          {isLoading ? (
            <p className="px-6 py-8 text-center text-sm text-slate-500">
              Loading documents…
            </p>
          ) : documents.length === 0 ? (
            <p className="px-6 py-8 text-center text-sm text-slate-500">
              {activeSearch || statusFilter
                ? "No documents match the current filter."
                : "No documents uploaded yet."}
            </p>
          ) : (
            <div className="divide-y divide-slate-100">
              {documents.map((doc) => {
                const busy = busyIds.has(doc.id);
                const actionError = actionErrors[doc.id];
                const chunks = chunkCounts[doc.id];

                return (
                  <div key={doc.id} className="px-6 py-5">
                    <div className="flex flex-wrap items-start justify-between gap-4">
                      {/* Left: document info */}
                      <div className="min-w-0 flex-1">
                        <p
                          className="truncate font-medium text-slate-900"
                          title={doc.original_filename}
                        >
                          {doc.original_filename}
                        </p>
                        <div className="mt-1 flex flex-wrap gap-x-4 gap-y-1 text-xs text-slate-500">
                          <span>{formatBytes(doc.file_size)}</span>
                          {doc.page_count != null && (
                            <span>{doc.page_count} pages</span>
                          )}
                          {chunks != null && (
                            <span className="text-emerald-700">
                              {chunks.chunk_count} chunks in index
                            </span>
                          )}
                          <span>Uploaded {formatDate(doc.created_at)}</span>
                          {doc.ingested_at && (
                            <span>Indexed {formatDate(doc.ingested_at)}</span>
                          )}
                        </div>
                        {doc.status === "failed" && doc.error_message && (
                          <p className="mt-1 text-xs text-red-600" role="alert">
                            Error: {doc.error_message}
                          </p>
                        )}
                        {actionError && (
                          <p className="mt-1 text-xs text-red-600" role="alert">
                            {actionError}
                          </p>
                        )}
                      </div>

                      {/* Right: status + actions */}
                      <div className="flex shrink-0 flex-wrap items-center gap-2">
                        <StatusBadge status={doc.status} />

                        <button
                          type="button"
                          disabled={busy || doc.status === "processing"}
                          onClick={() => handleIngest(doc)}
                          className="rounded-lg border border-emerald-600 px-3 py-1.5 text-xs font-medium text-emerald-700 transition hover:bg-emerald-50 disabled:cursor-not-allowed disabled:opacity-40"
                          aria-label={`Re-ingest ${doc.original_filename}`}
                        >
                          {busy && doc.status === "processing"
                            ? "Running…"
                            : "Re-ingest"}
                        </button>

                        <button
                          type="button"
                          disabled={busy}
                          onClick={() => handleToggleActive(doc)}
                          className="rounded-lg border border-slate-300 px-3 py-1.5 text-xs font-medium text-slate-600 transition hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-40"
                          aria-label={
                            doc.is_active
                              ? `Deactivate ${doc.original_filename}`
                              : `Activate ${doc.original_filename}`
                          }
                        >
                          {doc.is_active ? "Deactivate" : "Activate"}
                        </button>

                        <button
                          type="button"
                          disabled={busy}
                          onClick={() => handleDeleteClick(doc)}
                          className="rounded-lg border border-red-300 px-3 py-1.5 text-xs font-medium text-red-600 transition hover:bg-red-50 disabled:cursor-not-allowed disabled:opacity-40"
                          aria-label={`Delete ${doc.original_filename}`}
                        >
                          Delete
                        </button>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </div>
    </>
  );
}
