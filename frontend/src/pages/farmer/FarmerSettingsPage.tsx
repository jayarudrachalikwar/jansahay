import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../../context/AuthContext";

interface SettingCardProps {
  title: string;
  description?: string;
  children: React.ReactNode;
}
function SettingCard({ title, description, children }: SettingCardProps) {
  return (
    <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
      <h2 className="text-base font-semibold text-slate-800">{title}</h2>
      {description && <p className="mt-1 text-sm text-slate-500">{description}</p>}
      <div className="mt-4">{children}</div>
    </div>
  );
}

function ComingSoonBadge() {
  return (
    <span className="inline-flex items-center rounded-full bg-amber-100 px-2.5 py-0.5 text-xs font-medium text-amber-800">
      Coming soon
    </span>
  );
}

export default function FarmerSettingsPage() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  function handleLogout() {
    logout();
    navigate("/login", { replace: true });
  }

  return (
    <div className="mx-auto max-w-2xl px-4 py-10">
      <div className="mb-6">
        <p className="text-xs font-semibold uppercase tracking-widest text-emerald-700">Preferences</p>
        <h1 className="mt-1 text-2xl font-bold text-slate-900">Settings</h1>
        <p className="mt-1 text-sm text-slate-500">Manage your JanSahay AI account and preferences.</p>
      </div>

      <div className="space-y-5">
        {/* Account info */}
        <SettingCard title="Account" description="Your JanSahay AI account details.">
          <dl className="divide-y divide-slate-100 text-sm">
            {[
              ["Name", user?.full_name ?? "—"],
              ["Email", user?.email ?? "—"],
              ["Role", user?.role ?? "—"],
            ].map(([k, v]) => (
              <div key={k} className="flex justify-between py-2.5">
                <dt className="text-slate-500">{k}</dt>
                <dd className="font-medium text-slate-800 capitalize">{v}</dd>
              </div>
            ))}
          </dl>
          <Link
            to="/profile"
            className="mt-4 inline-block rounded-lg border border-emerald-600 px-4 py-2 text-sm font-medium text-emerald-700 transition hover:bg-emerald-50"
          >
            Edit Farmer Profile
          </Link>
        </SettingCard>

        {/* Language */}
        <SettingCard
          title="Language Preference"
          description="Choose the language for recommendations and AI responses."
        >
          <div className="flex items-center gap-3">
            <select
              disabled
              defaultValue="en"
              aria-label="Language preference (coming soon)"
              className="rounded-lg border border-slate-300 bg-slate-50 px-3 py-2 text-sm text-slate-500 cursor-not-allowed"
            >
              <option value="en">English</option>
              <option value="hi">हिन्दी (Hindi)</option>
              <option value="te">తెలుగు (Telugu)</option>
            </select>
            <ComingSoonBadge />
          </div>
          <p className="mt-2 text-xs text-slate-400">
            Voice input already supports English, Hindi, and Telugu.
            Full UI language switching is planned for a future update.
          </p>
        </SettingCard>

        {/* Notifications */}
        <SettingCard
          title="Notifications"
          description="Control when JanSahay AI sends you updates."
        >
          <div className="space-y-3">
            {[
              "New schemes matching your profile",
              "Eligibility updates",
              "Application reminders",
            ].map((label) => (
              <label key={label} className="flex cursor-not-allowed items-center justify-between text-sm text-slate-500">
                <span className="flex items-center gap-2">
                  <input type="checkbox" disabled
                    className="h-4 w-4 rounded border-slate-300 cursor-not-allowed" />
                  {label}
                </span>
                <ComingSoonBadge />
              </label>
            ))}
          </div>
        </SettingCard>

        {/* Security & logout */}
        <SettingCard title="Security" description="Manage your session and account security.">
          <div className="flex flex-wrap gap-3">
            <button
              type="button"
              onClick={handleLogout}
              className="rounded-lg border border-rose-300 px-4 py-2 text-sm font-medium text-rose-600 transition hover:bg-rose-50"
            >
              Logout
            </button>
          </div>
          <p className="mt-2 text-xs text-slate-400">
            Logging out will end your current session. Your data remains saved.
          </p>
        </SettingCard>
      </div>

      <p className="mt-8 text-center text-xs text-slate-400">
        JanSahay AI — Development build
      </p>
    </div>
  );
}
