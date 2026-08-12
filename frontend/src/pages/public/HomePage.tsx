import { Link } from "react-router-dom";
import { useAuth } from "../../context/AuthContext";

const FEATURES = [
  {
    icon: "🎯",
    title: "Personalized Scheme Matching",
    description:
      "JanSahay AI analyses your farmer profile to surface the government schemes most relevant to your land, crops, and income.",
  },
  {
    icon: "✅",
    title: "Instant Eligibility Checking",
    description:
      "Know immediately whether you qualify for a scheme using our deterministic eligibility engine — no guesswork.",
  },
  {
    icon: "🎤",
    title: "Multilingual Voice Assistant",
    description:
      "Ask questions in English, Hindi, or Telugu and receive AI-powered answers backed by official scheme documentation.",
  },
  {
    icon: "📋",
    title: "Application Preparation",
    description:
      "Track your readiness with a per-scheme checklist. Know exactly what's missing before you visit the application office.",
  },
  {
    icon: "🔍",
    title: "Smart Recommendations",
    description:
      "Schemes are ranked by how well they match your profile. Eligible schemes come first with clear explanations.",
  },
  {
    icon: "📂",
    title: "Save & Organise",
    description:
      "Bookmark schemes you're interested in and come back anytime. Your saved schemes are always one tap away.",
  },
];

const STEPS = [
  {
    step: "1",
    title: "Create your farmer profile",
    description:
      "Enter your state, land size, crops, income, and other details. Takes about two minutes.",
  },
  {
    step: "2",
    title: "Get personalized recommendations",
    description:
      "JanSahay AI instantly matches your profile against available central and state government schemes.",
  },
  {
    step: "3",
    title: "Check eligibility and prepare",
    description:
      "See exactly which criteria you meet. Use the checklist to prepare everything before applying.",
  },
  {
    step: "4",
    title: "Ask the AI Assistant",
    description:
      "Have questions? Ask the voice-enabled AI assistant in your language. It draws on official scheme documents.",
  },
];

export default function HomePage() {
  const { isAuthenticated, user } = useAuth();

  return (
    <div className="min-h-screen">
      {/* ── Hero ───────────────────────────────────────────────────────── */}
      <section className="bg-gradient-to-b from-emerald-50 to-white border-b border-slate-100">
        <div className="mx-auto max-w-6xl px-4 py-16 sm:py-24">
          <div className="max-w-2xl">
            <span className="inline-flex items-center gap-1.5 rounded-full border border-emerald-200 bg-emerald-50 px-3 py-1 text-xs font-medium text-emerald-700">
              🌾 AI-powered scheme discovery
            </span>
            <h1 className="mt-4 text-4xl font-bold leading-tight tracking-tight text-slate-900 sm:text-5xl">
              Find government schemes made{" "}
              <span className="text-emerald-700">for farmers like you</span>
            </h1>
            <p className="mt-5 text-lg text-slate-600 leading-relaxed">
              JanSahay AI helps Indian farmers discover, check eligibility for, and
              prepare applications for Central and State government welfare schemes —
              in English, Hindi, and Telugu.
            </p>
            <div className="mt-8 flex flex-wrap gap-4">
              {isAuthenticated ? (
                <>
                  <Link
                    to="/dashboard"
                    className="rounded-lg bg-emerald-700 px-6 py-3 text-sm font-semibold text-white shadow-sm transition hover:bg-emerald-800"
                  >
                    Go to Dashboard
                  </Link>
                  <Link
                    to="/schemes"
                    className="rounded-lg border border-slate-300 bg-white px-6 py-3 text-sm font-semibold text-slate-700 shadow-sm transition hover:bg-slate-50"
                  >
                    Explore Schemes
                  </Link>
                </>
              ) : (
                <>
                  <Link
                    to="/register"
                    className="rounded-lg bg-emerald-700 px-6 py-3 text-sm font-semibold text-white shadow-sm transition hover:bg-emerald-800"
                  >
                    Get Started — It's Free
                  </Link>
                  <Link
                    to="/login"
                    className="rounded-lg border border-slate-300 bg-white px-6 py-3 text-sm font-semibold text-slate-700 shadow-sm transition hover:bg-slate-50"
                  >
                    Login
                  </Link>
                </>
              )}
            </div>
          </div>

          {/* Hero stat strip */}
          <div className="mt-12 grid grid-cols-2 gap-4 sm:grid-cols-4">
            {[
              { value: "Central + State", label: "Scheme coverage" },
              { value: "3 Languages", label: "English, Hindi, Telugu" },
              { value: "AI-Powered", label: "Eligibility engine" },
              { value: "Voice-Enabled", label: "Ask in your language" },
            ].map(({ value, label }) => (
              <div key={label} className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm text-center">
                <p className="text-sm font-bold text-emerald-700">{value}</p>
                <p className="mt-0.5 text-xs text-slate-500">{label}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── How it works ──────────────────────────────────────────────── */}
      <section className="mx-auto max-w-6xl px-4 py-16">
        <div className="text-center">
          <p className="text-xs font-semibold uppercase tracking-widest text-emerald-700">
            Simple process
          </p>
          <h2 className="mt-2 text-3xl font-bold text-slate-900">How JanSahay Works</h2>
          <p className="mt-3 text-slate-500 max-w-xl mx-auto">
            From profile setup to application readiness in four steps.
          </p>
        </div>
        <div className="mt-12 grid gap-6 sm:grid-cols-2 lg:grid-cols-4">
          {STEPS.map(({ step, title, description }) => (
            <div key={step} className="relative rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
              <div className="flex h-10 w-10 items-center justify-center rounded-full bg-emerald-100 text-lg font-bold text-emerald-700">
                {step}
              </div>
              <h3 className="mt-4 text-base font-semibold text-slate-900">{title}</h3>
              <p className="mt-2 text-sm text-slate-500 leading-relaxed">{description}</p>
            </div>
          ))}
        </div>
      </section>

      {/* ── Features ──────────────────────────────────────────────────── */}
      <section className="bg-slate-50 border-y border-slate-200">
        <div className="mx-auto max-w-6xl px-4 py-16">
          <div className="text-center">
            <p className="text-xs font-semibold uppercase tracking-widest text-emerald-700">
              Capabilities
            </p>
            <h2 className="mt-2 text-3xl font-bold text-slate-900">
              Everything a farmer needs
            </h2>
          </div>
          <div className="mt-12 grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
            {FEATURES.map(({ icon, title, description }) => (
              <div key={title} className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
                <span className="text-3xl" aria-hidden="true">{icon}</span>
                <h3 className="mt-3 text-base font-semibold text-slate-900">{title}</h3>
                <p className="mt-2 text-sm text-slate-500 leading-relaxed">{description}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── CTA banner ────────────────────────────────────────────────── */}
      <section className="mx-auto max-w-6xl px-4 py-16">
        <div className="rounded-2xl bg-emerald-700 px-8 py-12 text-center shadow-md">
          <h2 className="text-2xl font-bold text-white sm:text-3xl">
            Ready to discover your schemes?
          </h2>
          <p className="mt-3 text-emerald-100 max-w-lg mx-auto">
            Create your free farmer profile in minutes. JanSahay AI will immediately show
            you which government schemes you may be eligible for.
          </p>
          <div className="mt-8 flex flex-wrap justify-center gap-4">
            {isAuthenticated ? (
              <Link
                to={user?.role === "farmer" ? "/farmer/recommendations" : "/dashboard"}
                className="rounded-lg bg-white px-6 py-3 text-sm font-semibold text-emerald-700 shadow-sm transition hover:bg-emerald-50"
              >
                View My Recommendations
              </Link>
            ) : (
              <>
                <Link
                  to="/register"
                  className="rounded-lg bg-white px-6 py-3 text-sm font-semibold text-emerald-700 shadow-sm transition hover:bg-emerald-50"
                >
                  Create Free Account
                </Link>
                <Link
                  to="/login"
                  className="rounded-lg border border-emerald-500 px-6 py-3 text-sm font-semibold text-white transition hover:bg-emerald-600"
                >
                  Sign In
                </Link>
              </>
            )}
          </div>
        </div>
      </section>

      {/* ── Disclaimer ────────────────────────────────────────────────── */}
      <section className="mx-auto max-w-6xl px-4 pb-8">
        <p className="text-center text-xs text-slate-400">
          JanSahay AI is a development project. Scheme data shown is for demonstration
          purposes only and does not represent official government information.
          Always verify scheme details through official government portals.
        </p>
      </section>
    </div>
  );
}
