import { useState } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { useAuth } from "../../context/AuthContext";

interface NavLinkProps {
  to: string;
  children: React.ReactNode;
  onClick?: () => void;
}

function NavLink({ to, children, onClick }: NavLinkProps) {
  const { pathname } = useLocation();
  const active = pathname === to || (to !== "/" && pathname.startsWith(to));
  return (
    <Link
      to={to}
      onClick={onClick}
      className={`text-sm font-medium transition-colors ${
        active
          ? "text-emerald-700"
          : "text-slate-600 hover:text-emerald-700"
      }`}
    >
      {children}
    </Link>
  );
}

export default function Header() {
  const { isAuthenticated, user, logout } = useAuth();
  const navigate = useNavigate();
  const [mobileOpen, setMobileOpen] = useState(false);

  function handleLogout() {
    logout();
    navigate("/login", { replace: true });
    setMobileOpen(false);
  }

  const farmerLinks = [
    { to: "/dashboard", label: "Dashboard" },
    { to: "/schemes", label: "Schemes" },
    { to: "/farmer/recommendations", label: "Recommendations" },
    { to: "/farmer/applications", label: "Applications" },
    { to: "/farmer/saved", label: "Saved" },
    { to: "/assistant", label: "AI Assistant" },
  ];

  const adminLinks = [
    { to: "/dashboard", label: "Dashboard" },
    { to: "/admin/schemes", label: "Schemes" },
    { to: "/admin/documents", label: "Documents" },
    { to: "/admin/farmers", label: "Farmers" },
  ];

  const links =
    user?.role === "admin" ? adminLinks : user?.role === "farmer" ? farmerLinks : [];

  return (
    <header className="sticky top-0 z-50 border-b border-slate-200 bg-white shadow-sm">
      <div className="mx-auto flex max-w-6xl items-center justify-between px-4 py-3">
        {/* Logo */}
        <Link to="/" className="flex items-center gap-2" onClick={() => setMobileOpen(false)}>
          <span className="text-xl" aria-hidden="true">🌾</span>
          <div>
            <p className="text-base font-bold leading-none text-emerald-700">JanSahay AI</p>
            <p className="text-xs leading-none text-slate-500">Scheme Discovery</p>
          </div>
        </Link>

        {/* Desktop nav */}
        <nav className="hidden items-center gap-5 md:flex" aria-label="Main navigation">
          {isAuthenticated ? (
            <>
              {links.map((l) => (
                <NavLink key={l.to} to={l.to}>{l.label}</NavLink>
              ))}
              {user?.role === "farmer" && (
                <NavLink to="/profile">Profile</NavLink>
              )}
              <div className="ml-2 flex items-center gap-2 border-l border-slate-200 pl-4">
                <span className="text-xs text-slate-500 max-w-[120px] truncate">
                  {user?.full_name}
                </span>
                <button
                  type="button"
                  onClick={handleLogout}
                  className="rounded-md border border-slate-300 px-3 py-1.5 text-xs font-medium text-slate-600 transition hover:bg-slate-50"
                >
                  Logout
                </button>
              </div>
            </>
          ) : (
            <>
              <NavLink to="/login">Login</NavLink>
              <Link
                to="/register"
                className="rounded-lg bg-emerald-700 px-4 py-1.5 text-sm font-medium text-white transition hover:bg-emerald-800"
              >
                Get Started
              </Link>
            </>
          )}
        </nav>

        {/* Mobile hamburger */}
        <button
          type="button"
          className="flex h-9 w-9 items-center justify-center rounded-lg border border-slate-200 text-slate-600 md:hidden"
          aria-label={mobileOpen ? "Close menu" : "Open menu"}
          aria-expanded={mobileOpen}
          onClick={() => setMobileOpen((v) => !v)}
        >
          {mobileOpen ? (
            <svg className="h-5 w-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
            </svg>
          ) : (
            <svg className="h-5 w-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path strokeLinecap="round" strokeLinejoin="round" d="M4 6h16M4 12h16M4 18h16" />
            </svg>
          )}
        </button>
      </div>

      {/* Mobile drawer */}
      {mobileOpen && (
        <div className="border-t border-slate-200 bg-white px-4 py-4 md:hidden">
          <nav className="flex flex-col gap-4" aria-label="Mobile navigation">
            {isAuthenticated ? (
              <>
                {links.map((l) => (
                  <NavLink key={l.to} to={l.to} onClick={() => setMobileOpen(false)}>
                    {l.label}
                  </NavLink>
                ))}
                {user?.role === "farmer" && (
                  <NavLink to="/profile" onClick={() => setMobileOpen(false)}>Profile</NavLink>
                )}
                <hr className="border-slate-200" />
                <span className="text-xs text-slate-500">{user?.full_name} · {user?.role}</span>
                <button
                  type="button"
                  onClick={handleLogout}
                  className="w-fit rounded-md border border-slate-300 px-3 py-1.5 text-sm font-medium text-slate-600"
                >
                  Logout
                </button>
              </>
            ) : (
              <>
                <NavLink to="/login" onClick={() => setMobileOpen(false)}>Login</NavLink>
                <Link
                  to="/register"
                  onClick={() => setMobileOpen(false)}
                  className="w-fit rounded-lg bg-emerald-700 px-4 py-2 text-sm font-medium text-white"
                >
                  Get Started
                </Link>
              </>
            )}
          </nav>
        </div>
      )}
    </header>
  );
}
