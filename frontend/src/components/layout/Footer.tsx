import { Link } from "react-router-dom";

export default function Footer() {
  return (
    <footer className="border-t border-slate-200 bg-white">
      <div className="mx-auto max-w-6xl px-4 py-10">
        <div className="grid gap-8 sm:grid-cols-2 md:grid-cols-3">
          {/* Brand */}
          <div>
            <div className="flex items-center gap-2">
              <span className="text-xl" aria-hidden="true">🌾</span>
              <span className="text-base font-bold text-emerald-700">JanSahay AI</span>
            </div>
            <p className="mt-2 text-sm text-slate-500 leading-relaxed">
              Helping farmers discover and prepare for government welfare schemes through
              AI-powered recommendations.
            </p>
          </div>

          {/* Farmer links */}
          <div>
            <h3 className="text-xs font-semibold uppercase tracking-wide text-slate-700">
              For Farmers
            </h3>
            <ul className="mt-3 space-y-2 text-sm">
              {[
                { to: "/schemes", label: "Browse Schemes" },
                { to: "/farmer/recommendations", label: "My Recommendations" },
                { to: "/farmer/applications", label: "My Applications" },
                { to: "/assistant", label: "AI Assistant" },
              ].map(({ to, label }) => (
                <li key={to}>
                  <Link to={to} className="text-slate-500 hover:text-emerald-700 transition-colors">
                    {label}
                  </Link>
                </li>
              ))}
            </ul>
          </div>

          {/* Account links */}
          <div>
            <h3 className="text-xs font-semibold uppercase tracking-wide text-slate-700">
              Account
            </h3>
            <ul className="mt-3 space-y-2 text-sm">
              {[
                { to: "/login", label: "Login" },
                { to: "/register", label: "Register" },
                { to: "/profile", label: "My Profile" },
                { to: "/farmer/settings", label: "Settings" },
              ].map(({ to, label }) => (
                <li key={to}>
                  <Link to={to} className="text-slate-500 hover:text-emerald-700 transition-colors">
                    {label}
                  </Link>
                </li>
              ))}
            </ul>
          </div>
        </div>

        <div className="mt-8 border-t border-slate-100 pt-6 flex flex-wrap items-center justify-between gap-3">
          <p className="text-xs text-slate-400">
            © {new Date().getFullYear()} JanSahay AI. Development build — not an official government service.
          </p>
          <p className="text-xs text-slate-400">
            Scheme data shown is for demonstration purposes only.
          </p>
        </div>
      </div>
    </footer>
  );
}
