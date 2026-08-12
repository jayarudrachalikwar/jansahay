import { useEffect, useState } from "react";
import axios from "axios";
import { getFarmer, listFarmers } from "../../services/adminFarmerService";
import type { AdminFarmerDetail, AdminFarmerListItem } from "../../types/adminFarmer";

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function formatDate(iso: string | null): string {
  if (!iso) return "—";
  return new Date(iso).toLocaleDateString("en-IN", { dateStyle: "medium" });
}

function StatusBadge({ active }: { active: boolean }) {
  return (
    <span
      className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${
        active ? "bg-emerald-100 text-emerald-800" : "bg-slate-100 text-slate-500"
      }`}
    >
      {active ? "Active" : "Inactive"}
    </span>
  );
}

// ---------------------------------------------------------------------------
// Detail drawer
// ---------------------------------------------------------------------------

function FarmerDetailPanel({
  farmerId,
  onClose,
}: {
  farmerId: number;
  onClose: () => void;
}) {
  const [detail, setDetail] = useState<AdminFarmerDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setLoading(true);
    setError(null);
    getFarmer(farmerId)
      .then(setDetail)
      .catch((err) => {
        if (axios.isAxiosError(err)) {
          setError(err.response?.data?.detail ?? "Failed to load farmer details.");
        } else {
          setError("Failed to load farmer details.");
        }
      })
      .finally(() => setLoading(false));
  }, [farmerId]);

  const profile = detail?.farmer_profile;

  return (
    <div
      className="fixed inset-0 z-40 flex items-start justify-end bg-black/30"
      role="dialog"
      aria-modal="true"
      aria-label="Farmer detail"
    >
      <div className="h-full w-full max-w-md overflow-y-auto bg-white shadow-xl">
        <div className="flex items-center justify-between border-b border-slate-200 px-6 py-4">
          <h2 className="text-base font-semibold text-slate-900">Farmer Details</h2>
          <button
            type="button"
            onClick={onClose}
            className="rounded-lg border border-slate-300 px-3 py-1.5 text-sm text-slate-600 hover:bg-slate-50"
            aria-label="Close detail panel"
          >
            Close
          </button>
        </div>

        {loading && (
          <p className="px-6 py-8 text-center text-sm text-slate-500">Loading…</p>
        )}
        {error && (
          <p className="px-6 py-4 text-sm text-red-600" role="alert">
            {error}
          </p>
        )}

        {detail && !loading && (
          <div className="px-6 py-5 space-y-6">
            {/* Account */}
            <section>
              <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-500">
                Account
              </p>
              <dl className="space-y-2 text-sm">
                <div className="flex justify-between">
                  <dt className="text-slate-500">Name</dt>
                  <dd className="font-medium text-slate-900">{detail.full_name}</dd>
                </div>
                <div className="flex justify-between">
                  <dt className="text-slate-500">Email</dt>
                  <dd className="text-slate-900">{detail.email}</dd>
                </div>
                {detail.phone_number && (
                  <div className="flex justify-between">
                    <dt className="text-slate-500">Phone</dt>
                    <dd className="text-slate-900">{detail.phone_number}</dd>
                  </div>
                )}
                <div className="flex justify-between">
                  <dt className="text-slate-500">Status</dt>
                  <dd>
                    <StatusBadge active={detail.is_active} />
                  </dd>
                </div>
                <div className="flex justify-between">
                  <dt className="text-slate-500">Registered</dt>
                  <dd className="text-slate-900">{formatDate(detail.created_at)}</dd>
                </div>
              </dl>
            </section>

            {/* Profile */}
            {profile ? (
              <section>
                <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-500">
                  Farm Profile
                </p>
                <dl className="space-y-2 text-sm">
                  {[
                    ["State", profile.state],
                    ["District", profile.district],
                    ["Village", profile.village],
                    ["Gender", profile.gender],
                    ["Land Size", profile.land_size ? `${profile.land_size} ${profile.land_unit ?? ""}`.trim() : null],
                    ["Ownership", profile.land_ownership],
                    ["Primary Crop", profile.primary_crop],
                    ["Secondary Crop", profile.secondary_crop],
                    ["Farming Type", profile.farming_type],
                    ["Irrigation", profile.irrigation_type],
                    ["Soil Type", profile.soil_type],
                    ["Annual Income", profile.annual_income ? `₹ ${profile.annual_income}` : null],
                  ]
                    .filter(([, v]) => v)
                    .map(([label, value]) => (
                      <div key={label as string} className="flex justify-between">
                        <dt className="text-slate-500">{label}</dt>
                        <dd className="text-slate-900">{value}</dd>
                      </div>
                    ))}
                </dl>
              </section>
            ) : (
              <section>
                <p className="text-sm text-slate-500">No farm profile created yet.</p>
              </section>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Page
// ---------------------------------------------------------------------------

export default function AdminFarmersPage() {
  const [farmers, setFarmers] = useState<AdminFarmerListItem[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedId, setSelectedId] = useState<number | null>(null);

  useEffect(() => {
    listFarmers()
      .then((data) => setFarmers(data.farmers))
      .catch((err) => {
        if (axios.isAxiosError(err)) {
          setError(err.response?.data?.detail ?? "Failed to load farmers.");
        } else {
          setError("Failed to load farmers.");
        }
      })
      .finally(() => setIsLoading(false));
  }, []);

  return (
    <>
      {selectedId !== null && (
        <FarmerDetailPanel farmerId={selectedId} onClose={() => setSelectedId(null)} />
      )}

      <div className="mx-auto max-w-5xl px-4 py-10">
        <div className="mb-6 flex flex-col gap-1">
          <p className="text-sm font-medium uppercase tracking-wide text-emerald-700">Admin</p>
          <h1 className="text-2xl font-bold text-slate-900">Farmer Accounts</h1>
          <p className="text-sm text-slate-500">
            Registered farmer accounts and their profile status.
          </p>
        </div>

        <div className="rounded-xl border border-slate-200 bg-white shadow-sm">
          <div className="border-b border-slate-100 px-6 py-4">
            <h2 className="text-base font-semibold text-slate-800">
              Farmers{" "}
              <span className="ml-1 text-sm font-normal text-slate-400">
                ({farmers.length})
              </span>
            </h2>
          </div>

          {isLoading && (
            <p className="px-6 py-8 text-center text-sm text-slate-500">Loading farmers…</p>
          )}

          {error && (
            <p className="px-6 py-4 text-sm text-red-600" role="alert">
              {error}
            </p>
          )}

          {!isLoading && !error && farmers.length === 0 && (
            <p className="px-6 py-8 text-center text-sm text-slate-500">
              No farmer accounts registered yet.
            </p>
          )}

          {!isLoading && !error && farmers.length > 0 && (
            <div className="divide-y divide-slate-100">
              {farmers.map((farmer) => (
                <div key={farmer.id} className="flex flex-wrap items-center justify-between gap-4 px-6 py-4">
                  <div className="min-w-0">
                    <p className="font-medium text-slate-900">{farmer.full_name}</p>
                    <p className="text-sm text-slate-500">{farmer.email}</p>
                    <div className="mt-1 flex flex-wrap gap-x-3 gap-y-0.5 text-xs text-slate-500">
                      {farmer.state && <span>{farmer.state}</span>}
                      {farmer.primary_crop && <span>Crop: {farmer.primary_crop}</span>}
                      <span>Joined {formatDate(farmer.created_at)}</span>
                    </div>
                  </div>

                  <div className="flex shrink-0 items-center gap-3">
                    <span
                      className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${
                        farmer.has_profile
                          ? "bg-emerald-100 text-emerald-800"
                          : "bg-yellow-100 text-yellow-800"
                      }`}
                    >
                      {farmer.has_profile ? "Profile complete" : "No profile"}
                    </span>
                    <StatusBadge active={farmer.is_active} />
                    <button
                      type="button"
                      onClick={() => setSelectedId(farmer.id)}
                      className="rounded-lg border border-slate-300 px-3 py-1.5 text-xs font-medium text-slate-600 hover:bg-slate-50"
                      aria-label={`View details for ${farmer.full_name}`}
                    >
                      View
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
