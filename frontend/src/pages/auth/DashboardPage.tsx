import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import axios from "axios";
import RecommendationCard from "../../components/schemes/RecommendationCard";
import { useAuth } from "../../context/AuthContext";
import { getProfile, getProfileCompletion } from "../../services/profileService";
import { getSchemeRecommendations } from "../../services/schemeService";
import { listSavedSchemes } from "../../services/savedSchemeService";
import { getApplicationSummary } from "../../services/applicationService";
import type { FarmerProfile } from "../../types/profile";
import type { SchemeRecommendation } from "../../types/scheme";
import type { ApplicationSummary } from "../../types/application";

function displayValue(v: string | null | undefined) {
  return v?.trim() ? v : "—";
}
function formatLandSize(p: FarmerProfile | null) {
  if (!p?.land_size) return "—";
  return `${p.land_size}${p.land_unit ? " " + p.land_unit : ""}`;
}

interface StatPillProps {
  label: string;
  value: string | number;
  to: string;
  color?: string;
}
function StatPill({ label, value, to, color = "bg-slate-100 text-slate-700" }: StatPillProps) {
  return (
    <Link to={to} className={`inline-flex items-center gap-1.5 rounded-full px-3 py-1.5 text-xs font-medium transition hover:opacity-80 ${color}`}>
      <span className="font-bold">{value}</span>
      <span>{label}</span>
    </Link>
  );
}

interface QuickActionProps {
  to: string;
  icon: string;
  label: string;
  description: string;
  primary?: boolean;
}
function QuickAction({ to, icon, label, description, primary }: QuickActionProps) {
  return (
    <Link
      to={to}
      className={`flex flex-col gap-1.5 rounded-xl border p-4 transition hover:shadow-md ${
        primary
          ? "border-emerald-200 bg-emerald-50 hover:bg-emerald-100"
          : "border-slate-200 bg-white hover:bg-slate-50"
      }`}
    >
      <span className="text-2xl" aria-hidden="true">{icon}</span>
      <span className={`text-sm font-semibold ${primary ? "text-emerald-800" : "text-slate-800"}`}>
        {label}
      </span>
      <span className="text-xs text-slate-500 leading-relaxed">{description}</span>
    </Link>
  );
}

export default function DashboardPage() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [profile, setProfile] = useState<FarmerProfile | null>(null);
  const [completion, setCompletion] = useState(0);
  const [recommendations, setRecommendations] = useState<SchemeRecommendation[]>([]);
  const [recsMessage, setRecsMessage] = useState<string | null>(null);
  const [savedCount, setSavedCount] = useState<number | null>(null);
  const [appSummary, setAppSummary] = useState<ApplicationSummary | null>(null);
  const [isLoading, setIsLoading] = useState(user?.role === "farmer");

  useEffect(() => {
    if (user?.role !== "farmer") return;
    async function load() {
      try {
        const comp = await getProfileCompletion();
        setCompletion(comp.completion_percentage);
        try {
          const p = await getProfile();
          setProfile(p);
          try {
            const recs = await getSchemeRecommendations();
            setRecommendations(recs.recommendations.slice(0, 3));
          } catch (e) {
            if (axios.isAxiosError(e) && e.response?.status === 404) {
              setRecsMessage("Complete your farmer profile to receive personalized scheme recommendations.");
            }
          }
          try { const s = await listSavedSchemes(); setSavedCount(s.total); } catch { /* non-fatal */ }
          try { const a = await getApplicationSummary(); setAppSummary(a); } catch { /* non-fatal */ }
        } catch (e) {
          if (axios.isAxiosError(e) && e.response?.status === 404) {
            setRecsMessage("Complete your farmer profile to receive personalized scheme recommendations.");
          }
        }
      } finally {
        setIsLoading(false);
      }
    }
    load();
  }, [user?.role]);

  if (!user) return null;

  if (user.role === "admin") {
    return (
      <div className="mx-auto max-w-3xl px-4 py-12">
        <div className="rounded-2xl border border-slate-200 bg-white p-8 shadow-sm">
          <p className="text-xs font-semibold uppercase tracking-widest text-emerald-700">Admin Portal</p>
          <h1 className="mt-2 text-2xl font-bold text-slate-900">Welcome, {user.full_name}</h1>
          <dl className="mt-6 divide-y divide-slate-100 text-sm">
            {[["Email", user.email], ["Role", "Administrator"]].map(([k, v]) => (
              <div key={k} className="flex justify-between py-3">
                <dt className="font-medium text-slate-500">{k}</dt>
                <dd className="text-slate-900 capitalize">{v}</dd>
              </div>
            ))}
          </dl>
          <div className="mt-8 flex flex-wrap gap-3">
            <Link to="/admin/schemes" className="rounded-lg bg-emerald-700 px-4 py-2 text-sm font-medium text-white hover:bg-emerald-800">Manage Schemes</Link>
            <Link to="/admin/documents" className="rounded-lg border border-emerald-700 px-4 py-2 text-sm font-medium text-emerald-700 hover:bg-emerald-50">Documents</Link>
            <Link to="/admin/farmers" className="rounded-lg border border-slate-300 px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50">View Farmers</Link>
          </div>
          <button type="button" onClick={() => { logout(); navigate("/login", { replace: true }); }}
            className="mt-6 text-sm text-slate-500 hover:text-rose-600 transition">
            Logout
          </button>
        </div>
      </div>
    );
  }

  if (isLoading) {
    return (
      <div className="mx-auto max-w-5xl px-4 py-16 text-center">
        <div className="inline-flex items-center gap-2 text-sm text-slate-500">
          <span className="animate-spin">⏳</span> Loading dashboard…
        </div>
      </div>
    );
  }

  const completionColor = completion >= 80 ? "bg-emerald-500" : completion >= 40 ? "bg-amber-400" : "bg-rose-400";

  return (
    <div className="mx-auto max-w-5xl px-4 py-10 space-y-8">

      {/* ── Welcome header ─────────────────────────────────────────── */}
      <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm sm:p-8">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <p className="text-xs font-semibold uppercase tracking-widest text-emerald-700">JanSahay AI</p>
            <h1 className="mt-1 text-2xl font-bold text-slate-900">Welcome back, {user.full_name}</h1>
            <p className="mt-1 text-sm text-slate-500">Government welfare scheme discovery for farmers</p>
          </div>
          {/* Stat pills */}
          <div className="flex flex-wrap gap-2">
            {savedCount !== null && (
              <StatPill to="/farmer/saved" value={savedCount} label="saved" color="bg-slate-100 text-slate-700" />
            )}
            {recommendations.length > 0 && (
              <StatPill to="/farmer/recommendations" value={recommendations.length} label="recommendations" color="bg-emerald-100 text-emerald-800" />
            )}
            {appSummary && appSummary.total > 0 && (
              <StatPill to="/farmer/applications" value={appSummary.total} label="applications" color="bg-blue-100 text-blue-800" />
            )}
          </div>
        </div>

        {/* Profile completion */}
        <div className="mt-6">
          <div className="flex items-center justify-between text-sm mb-1.5">
            <span className="font-medium text-slate-700">Profile completion</span>
            <span className={`font-semibold ${completion >= 80 ? "text-emerald-700" : completion >= 40 ? "text-amber-600" : "text-rose-600"}`}>
              {completion}%
            </span>
          </div>
          <div className="h-2.5 overflow-hidden rounded-full bg-slate-100">
            <div
              className={`h-full rounded-full transition-all ${completionColor}`}
              style={{ width: `${completion}%` }}
              role="progressbar"
              aria-valuenow={completion}
              aria-valuemin={0}
              aria-valuemax={100}
            />
          </div>
          {completion < 100 && (
            <p className="mt-1.5 text-xs text-slate-400">
              A complete profile improves your scheme recommendations.{" "}
              <Link to="/profile" className="text-emerald-700 underline">Update now</Link>
            </p>
          )}
        </div>
      </section>

      {/* ── Quick actions ───────────────────────────────────────────── */}
      <section>
        <h2 className="mb-4 text-base font-semibold text-slate-800">Quick Actions</h2>
        <div className="grid gap-4 grid-cols-2 sm:grid-cols-4">
          <QuickAction to="/assistant" icon="🎤" label="Ask JanSahay" description="Talk to the AI assistant" primary />
          <QuickAction to="/farmer/recommendations" icon="🎯" label="Recommendations" description="Schemes matched to your profile" />
          <QuickAction to="/schemes" icon="🔍" label="Browse Schemes" description="Search all available schemes" />
          <QuickAction to="/farmer/applications" icon="📋" label="Applications" description="Track your application readiness" />
        </div>
      </section>

      {/* ── Profile summary ─────────────────────────────────────────── */}
      <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
        <div className="flex items-center justify-between mb-5">
          <h2 className="text-base font-semibold text-slate-800">Profile Summary</h2>
          <Link to="/profile" className="text-xs font-medium text-emerald-700 hover:underline">
            {profile ? "Edit Profile" : "Complete Profile →"}
          </Link>
        </div>
        <dl className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3 text-sm">
          {[
            ["State", displayValue(profile?.state)],
            ["District", displayValue(profile?.district)],
            ["Primary Crop", displayValue(profile?.primary_crop)],
            ["Land Size", formatLandSize(profile)],
            ["Farming Type", displayValue(profile?.farming_type)],
            ["Irrigation", displayValue(profile?.irrigation_type)],
          ].map(([label, value]) => (
            <div key={label} className="rounded-lg bg-slate-50 px-3 py-2.5">
              <dt className="text-xs text-slate-500">{label}</dt>
              <dd className="mt-0.5 font-medium text-slate-800">{value}</dd>
            </div>
          ))}
        </dl>
      </section>

      {/* ── Top recommendations ─────────────────────────────────────── */}
      <section>
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-base font-semibold text-slate-800">Top Recommendations</h2>
          <Link to="/farmer/recommendations" className="text-xs font-medium text-emerald-700 hover:underline">
            View all →
          </Link>
        </div>
        {recsMessage && (
          <div className="rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800">
            {recsMessage}{" "}
            <Link to="/profile" className="font-semibold underline">Complete profile</Link>
          </div>
        )}
        {!recsMessage && recommendations.length === 0 && (
          <div className="rounded-xl border border-slate-200 bg-white p-6 text-center text-sm text-slate-500">
            No recommendations yet.{" "}
            <Link to="/schemes" className="text-emerald-700 underline">Browse all schemes</Link>
          </div>
        )}
        {recommendations.length > 0 && (
          <div className="space-y-4">
            {recommendations.map((rec) => (
              <RecommendationCard key={rec.scheme.id} recommendation={rec} />
            ))}
          </div>
        )}
      </section>
    </div>
  );
}
