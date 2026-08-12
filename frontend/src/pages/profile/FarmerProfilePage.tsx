import { FormEvent, useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import axios from "axios";
import { createProfile, getProfile, updateProfile } from "../../services/profileService";
import type { FarmerProfile, FarmerProfilePayload } from "../../types/profile";

const emptyForm: FarmerProfilePayload = {
  date_of_birth: "", gender: "", state: "", district: "", village: "",
  land_size: null, land_unit: "", land_ownership: "",
  primary_crop: "", secondary_crop: "", soil_type: "", irrigation_type: "",
  farming_type: "", annual_income: null,
};

function profileToForm(p: FarmerProfile): FarmerProfilePayload {
  return {
    date_of_birth: p.date_of_birth ?? "", gender: p.gender ?? "",
    state: p.state ?? "", district: p.district ?? "", village: p.village ?? "",
    land_size: p.land_size, land_unit: p.land_unit ?? "",
    land_ownership: p.land_ownership ?? "", primary_crop: p.primary_crop ?? "",
    secondary_crop: p.secondary_crop ?? "", soil_type: p.soil_type ?? "",
    irrigation_type: p.irrigation_type ?? "", farming_type: p.farming_type ?? "",
    annual_income: p.annual_income,
  };
}

function formToPayload(f: FarmerProfilePayload): FarmerProfilePayload {
  return {
    date_of_birth: f.date_of_birth || null, gender: f.gender || null,
    state: f.state || null, district: f.district || null, village: f.village || null,
    land_size: f.land_size == null ? null : Number(f.land_size),
    land_unit: f.land_unit || null, land_ownership: f.land_ownership || null,
    primary_crop: f.primary_crop || null, secondary_crop: f.secondary_crop || null,
    soil_type: f.soil_type || null, irrigation_type: f.irrigation_type || null,
    farming_type: f.farming_type || null,
    annual_income: f.annual_income == null ? null : Number(f.annual_income),
  };
}

function getErrorMessage(error: unknown) {
  if (axios.isAxiosError(error)) {
    const d = error.response?.data?.detail;
    if (typeof d === "string") return d;
  }
  return "Unable to save profile. Please check your details and try again.";
}

interface SectionProps { title: string; children: React.ReactNode }
function Section({ title, children }: SectionProps) {
  return (
    <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
      <h2 className="mb-4 text-sm font-semibold uppercase tracking-wide text-emerald-700">{title}</h2>
      <div className="grid gap-4 sm:grid-cols-2">{children}</div>
    </div>
  );
}

interface FieldProps {
  id: string; label: string; type?: string;
  value: string | number | null | undefined; onChange: (v: string) => void;
  placeholder?: string; required?: boolean; step?: string;
}
function Field({ id, label, type = "text", value, onChange, placeholder, step }: FieldProps) {
  return (
    <div>
      <label htmlFor={id} className="block text-sm font-medium text-slate-700">{label}</label>
      <input
        id={id} type={type} step={step}
        value={value ?? ""}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        className="mt-1.5 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm text-slate-900 outline-none transition focus:border-emerald-500 focus:ring-2 focus:ring-emerald-500/20"
      />
    </div>
  );
}

interface SelectFieldProps {
  id: string; label: string; value: string | null | undefined;
  onChange: (v: string) => void; options: { value: string; label: string }[];
}
function SelectField({ id, label, value, onChange, options }: SelectFieldProps) {
  return (
    <div>
      <label htmlFor={id} className="block text-sm font-medium text-slate-700">{label}</label>
      <select
        id={id} value={value ?? ""}
        onChange={(e) => onChange(e.target.value)}
        className="mt-1.5 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm text-slate-900 outline-none transition focus:border-emerald-500 focus:ring-2 focus:ring-emerald-500/20 bg-white"
      >
        <option value="">Select…</option>
        {options.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
      </select>
    </div>
  );
}

export default function FarmerProfilePage() {
  const navigate = useNavigate();
  const [form, setForm] = useState<FarmerProfilePayload>(emptyForm);
  const [isEditing, setIsEditing] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  useEffect(() => {
    async function load() {
      try {
        const p = await getProfile();
        setForm(profileToForm(p));
        setIsEditing(true);
      } catch (e) {
        if (!axios.isAxiosError(e) || e.response?.status !== 404) setError(getErrorMessage(e));
      } finally { setIsLoading(false); }
    }
    load();
  }, []);

  function set<K extends keyof FarmerProfilePayload>(k: K, v: FarmerProfilePayload[K]) {
    setForm((f) => ({ ...f, [k]: v }));
  }

  async function handleSubmit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setError(null); setSuccess(null); setIsSubmitting(true);
    try {
      const payload = formToPayload(form);
      if (isEditing) { await updateProfile(payload); setSuccess("Profile updated."); }
      else { await createProfile(payload); setIsEditing(true); setSuccess("Profile saved."); }
    } catch (e) { setError(getErrorMessage(e)); }
    finally { setIsSubmitting(false); }
  }

  if (isLoading) {
    return <div className="mx-auto max-w-3xl px-4 py-16 text-center text-sm text-slate-500">Loading profile…</div>;
  }

  return (
    <div className="mx-auto max-w-3xl px-4 py-10">
      <div className="mb-6 flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="text-xs font-semibold uppercase tracking-widest text-emerald-700">Farmer Profile</p>
          <h1 className="mt-1 text-2xl font-bold text-slate-900">
            {isEditing ? "Edit your profile" : "Complete your profile"}
          </h1>
          <p className="mt-1 text-sm text-slate-500">
            Your profile is used to match you with relevant government schemes.
          </p>
        </div>
        <Link to="/dashboard" className="text-sm font-medium text-emerald-700 hover:underline">← Dashboard</Link>
      </div>

      <form className="space-y-5" onSubmit={handleSubmit}>
        <Section title="Personal Information">
          <Field id="date_of_birth" label="Date of Birth" type="date"
            value={form.date_of_birth ?? ""} onChange={(v) => set("date_of_birth", v)} />
          <SelectField id="gender" label="Gender" value={form.gender}
            onChange={(v) => set("gender", v)}
            options={[{ value: "male", label: "Male" }, { value: "female", label: "Female" }, { value: "other", label: "Other" }]} />
        </Section>

        <Section title="Location">
          <Field id="state" label="State" value={form.state} onChange={(v) => set("state", v)} placeholder="e.g. Telangana" />
          <Field id="district" label="District" value={form.district} onChange={(v) => set("district", v)} placeholder="e.g. Hyderabad" />
          <div className="sm:col-span-2">
            <Field id="village" label="Village" value={form.village} onChange={(v) => set("village", v)} placeholder="Your village name" />
          </div>
        </Section>

        <Section title="Land & Farming">
          <Field id="land_size" label="Land Size" type="number" step="0.01"
            value={form.land_size} onChange={(v) => set("land_size", v === "" ? null : Number(v))}
            placeholder="e.g. 2.5" />
          <SelectField id="land_unit" label="Land Unit" value={form.land_unit}
            onChange={(v) => set("land_unit", v)}
            options={[{ value: "acres", label: "Acres" }, { value: "hectares", label: "Hectares" }, { value: "bigha", label: "Bigha" }]} />
          <SelectField id="land_ownership" label="Land Ownership" value={form.land_ownership}
            onChange={(v) => set("land_ownership", v)}
            options={[{ value: "owned", label: "Owned" }, { value: "leased", label: "Leased" }, { value: "shared", label: "Shared" }]} />
          <SelectField id="farming_type" label="Farming Type" value={form.farming_type}
            onChange={(v) => set("farming_type", v)}
            options={[{ value: "organic", label: "Organic" }, { value: "conventional", label: "Conventional" }, { value: "mixed", label: "Mixed" }, { value: "subsistence", label: "Subsistence" }, { value: "commercial", label: "Commercial" }]} />
          <SelectField id="irrigation_type" label="Irrigation Type" value={form.irrigation_type}
            onChange={(v) => set("irrigation_type", v)}
            options={[{ value: "drip", label: "Drip" }, { value: "sprinkler", label: "Sprinkler" }, { value: "flood", label: "Flood" }, { value: "rainfed", label: "Rainfed" }, { value: "canal", label: "Canal" }, { value: "borewell", label: "Borewell" }]} />
          <SelectField id="soil_type" label="Soil Type" value={form.soil_type}
            onChange={(v) => set("soil_type", v)}
            options={[{ value: "black", label: "Black" }, { value: "red", label: "Red" }, { value: "alluvial", label: "Alluvial" }, { value: "loamy", label: "Loamy" }, { value: "sandy", label: "Sandy" }]} />
        </Section>

        <Section title="Crops">
          <Field id="primary_crop" label="Primary Crop" value={form.primary_crop}
            onChange={(v) => set("primary_crop", v)} placeholder="e.g. Cotton" />
          <Field id="secondary_crop" label="Secondary Crop (optional)" value={form.secondary_crop}
            onChange={(v) => set("secondary_crop", v)} placeholder="e.g. Wheat" />
        </Section>

        <Section title="Financial Information">
          <Field id="annual_income" label="Annual Income (₹)" type="number" step="1"
            value={form.annual_income} onChange={(v) => set("annual_income", v === "" ? null : Number(v))}
            placeholder="e.g. 150000" />
        </Section>

        {error && (
          <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700" role="alert">{error}</div>
        )}
        {success && (
          <div className="rounded-lg border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-700" role="status">{success}</div>
        )}

        <div className="flex flex-wrap gap-3">
          <button type="submit" disabled={isSubmitting}
            className="rounded-lg bg-emerald-700 px-5 py-2.5 text-sm font-semibold text-white shadow-sm transition hover:bg-emerald-800 disabled:cursor-not-allowed disabled:opacity-60">
            {isSubmitting ? "Saving…" : isEditing ? "Update Profile" : "Save Profile"}
          </button>
          <button type="button" onClick={() => navigate("/dashboard")}
            className="rounded-lg border border-slate-300 px-5 py-2.5 text-sm font-medium text-slate-700 transition hover:bg-slate-50">
            Cancel
          </button>
        </div>
      </form>
    </div>
  );
}
