import { useCallback, useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import axios from "axios";
import {
  createAdminScheme,
  getAdminScheme,
  updateAdminScheme,
} from "../../services/adminSchemeService";
import type {
  AdminEligibilityCriterionInput,
  AdminSchemePayload,
} from "../../types/adminScheme";

// ---------------------------------------------------------------------------
// Empty defaults
// ---------------------------------------------------------------------------

const EMPTY_CRITERION: AdminEligibilityCriterionInput = {
  criterion_type: "profile",
  field_name: "",
  operator: "equals",
  expected_value: "",
  description: null,
};

const EMPTY_FORM: AdminSchemePayload = {
  name: "",
  short_description: "",
  detailed_description: "",
  department: "",
  state: "",
  scheme_type: "",
  benefits: "",
  application_process: "",
  official_website: null,
  is_active: true,
  eligibility_criteria: [],
};

// Common operator options — shown as hints; backend accepts any string
const OPERATOR_OPTIONS = [
  "equals",
  "not_equals",
  "greater_than",
  "less_than",
  "greater_than_or_equal",
  "less_than_or_equal",
  "contains",
  "in",
];

// ---------------------------------------------------------------------------
// Field wrappers
// ---------------------------------------------------------------------------

function Field({
  label,
  required,
  children,
  error,
}: {
  label: string;
  required?: boolean;
  children: React.ReactNode;
  error?: string;
}) {
  return (
    <div>
      <label className="mb-1 block text-sm font-medium text-slate-700">
        {label}
        {required && <span className="ml-0.5 text-red-500">*</span>}
      </label>
      {children}
      {error && (
        <p className="mt-1 text-xs text-red-600" role="alert">
          {error}
        </p>
      )}
    </div>
  );
}

const inputCls =
  "w-full rounded-lg border border-slate-300 px-3 py-2 text-sm text-slate-900 placeholder-slate-400 focus:border-emerald-500 focus:outline-none focus:ring-1 focus:ring-emerald-500";

const textareaCls = inputCls + " resize-y min-h-[80px]";

// ---------------------------------------------------------------------------
// Page
// ---------------------------------------------------------------------------

export default function AdminSchemeFormPage() {
  const { id } = useParams<{ id: string }>();
  const isEdit = Boolean(id);
  const navigate = useNavigate();

  const [form, setForm] = useState<AdminSchemePayload>(EMPTY_FORM);
  const [isLoadingScheme, setIsLoadingScheme] = useState(isEdit);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});

  // Load existing scheme for edit
  const loadScheme = useCallback(async () => {
    if (!id) return;
    setIsLoadingScheme(true);
    try {
      const scheme = await getAdminScheme(Number(id));
      setForm({
        name: scheme.name,
        short_description: scheme.short_description,
        detailed_description: scheme.detailed_description,
        department: scheme.department,
        state: scheme.state,
        scheme_type: scheme.scheme_type,
        benefits: scheme.benefits,
        application_process: scheme.application_process,
        official_website: scheme.official_website ?? null,
        is_active: scheme.is_active,
        eligibility_criteria: scheme.eligibility_criteria.map((c) => ({
          criterion_type: c.criterion_type,
          field_name: c.field_name,
          operator: c.operator,
          expected_value: c.expected_value,
          description: c.description ?? null,
        })),
      });
    } catch (err) {
      setSubmitError(
        axios.isAxiosError(err)
          ? (err.response?.data?.detail ?? "Failed to load scheme.")
          : "Failed to load scheme."
      );
    } finally {
      setIsLoadingScheme(false);
    }
  }, [id]);

  useEffect(() => {
    if (isEdit) loadScheme();
  }, [isEdit, loadScheme]);

  // ---------------------------------------------------------------------------
  // Field handlers
  // ---------------------------------------------------------------------------

  function setField<K extends keyof AdminSchemePayload>(
    key: K,
    value: AdminSchemePayload[K],
  ) {
    setForm((prev) => ({ ...prev, [key]: value }));
    setFieldErrors((prev) => {
      const next = { ...prev };
      delete next[key];
      return next;
    });
  }

  function setCriterionField(
    index: number,
    key: keyof AdminEligibilityCriterionInput,
    value: string | null,
  ) {
    setForm((prev) => {
      const criteria = [...prev.eligibility_criteria];
      criteria[index] = { ...criteria[index], [key]: value };
      return { ...prev, eligibility_criteria: criteria };
    });
  }

  function addCriterion() {
    setForm((prev) => ({
      ...prev,
      eligibility_criteria: [
        ...prev.eligibility_criteria,
        { ...EMPTY_CRITERION },
      ],
    }));
  }

  function removeCriterion(index: number) {
    setForm((prev) => ({
      ...prev,
      eligibility_criteria: prev.eligibility_criteria.filter(
        (_, i) => i !== index,
      ),
    }));
  }

  // ---------------------------------------------------------------------------
  // Client-side validation
  // ---------------------------------------------------------------------------

  function validate(): boolean {
    const errors: Record<string, string> = {};
    const required: Array<keyof AdminSchemePayload> = [
      "name",
      "short_description",
      "detailed_description",
      "department",
      "state",
      "scheme_type",
      "benefits",
      "application_process",
    ];
    for (const key of required) {
      const val = form[key];
      if (typeof val === "string" && !val.trim()) {
        errors[key] = "This field is required.";
      }
    }

    form.eligibility_criteria.forEach((c, i) => {
      if (!c.field_name.trim())
        errors[`criteria_${i}_field_name`] = "Field name is required.";
      if (!c.operator.trim())
        errors[`criteria_${i}_operator`] = "Operator is required.";
      if (!c.expected_value.trim())
        errors[`criteria_${i}_expected_value`] = "Expected value is required.";
    });

    setFieldErrors(errors);
    return Object.keys(errors).length === 0;
  }

  // ---------------------------------------------------------------------------
  // Submit
  // ---------------------------------------------------------------------------

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!validate()) return;

    setIsSubmitting(true);
    setSubmitError(null);

    // Normalise optional empty string to null
    const payload: AdminSchemePayload = {
      ...form,
      official_website:
        form.official_website?.trim() ? form.official_website.trim() : null,
    };

    try {
      if (isEdit && id) {
        await updateAdminScheme(Number(id), payload);
      } else {
        await createAdminScheme(payload);
      }
      navigate("/admin/schemes");
    } catch (err) {
      if (axios.isAxiosError(err)) {
        const detail = err.response?.data?.detail;
        if (Array.isArray(detail)) {
          // Pydantic validation errors → field-level display
          const newErrors: Record<string, string> = {};
          for (const item of detail) {
            const loc = item.loc?.slice(1).join("_") ?? "form";
            newErrors[loc] = item.msg ?? "Invalid value.";
          }
          setFieldErrors(newErrors);
          setSubmitError("Please fix the errors below.");
        } else {
          setSubmitError(
            typeof detail === "string" ? detail : "Save failed.",
          );
        }
      } else {
        setSubmitError("Save failed. Please try again.");
      }
    } finally {
      setIsSubmitting(false);
    }
  }

  // ---------------------------------------------------------------------------
  // Render
  // ---------------------------------------------------------------------------

  if (isLoadingScheme) {
    return (
      <div className="mx-auto max-w-3xl px-4 py-10">
        <p className="text-sm text-slate-500">Loading scheme…</p>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-3xl px-4 py-10">
      <div className="mb-6">
        <p className="text-sm font-medium uppercase tracking-wide text-emerald-700">
          Admin
        </p>
        <h1 className="text-2xl font-bold text-slate-900">
          {isEdit ? "Edit Scheme" : "New Scheme"}
        </h1>
      </div>

      <form onSubmit={handleSubmit} noValidate>
        <div className="space-y-5 rounded-xl border border-slate-200 bg-white p-6 shadow-sm">

          {/* Core fields */}
          <Field label="Scheme name" required error={fieldErrors.name}>
            <input
              type="text"
              value={form.name}
              onChange={(e) => setField("name", e.target.value)}
              className={inputCls}
              placeholder="e.g. PM Kisan Samman Nidhi"
              aria-required="true"
            />
          </Field>

          <Field
            label="Short description"
            required
            error={fieldErrors.short_description}
          >
            <input
              type="text"
              value={form.short_description}
              onChange={(e) => setField("short_description", e.target.value)}
              className={inputCls}
              placeholder="One-line description shown in listings"
              aria-required="true"
            />
          </Field>

          <Field
            label="Detailed description"
            required
            error={fieldErrors.detailed_description}
          >
            <textarea
              value={form.detailed_description}
              onChange={(e) => setField("detailed_description", e.target.value)}
              className={textareaCls}
              placeholder="Full scheme description"
              aria-required="true"
            />
          </Field>

          <div className="grid grid-cols-1 gap-5 sm:grid-cols-2">
            <Field label="Department" required error={fieldErrors.department}>
              <input
                type="text"
                value={form.department}
                onChange={(e) => setField("department", e.target.value)}
                className={inputCls}
                placeholder="e.g. Ministry of Agriculture"
                aria-required="true"
              />
            </Field>
            <Field label="State" required error={fieldErrors.state}>
              <input
                type="text"
                value={form.state}
                onChange={(e) => setField("state", e.target.value)}
                className={inputCls}
                placeholder="e.g. All India"
                aria-required="true"
              />
            </Field>
          </div>

          <Field label="Scheme type" required error={fieldErrors.scheme_type}>
            <input
              type="text"
              value={form.scheme_type}
              onChange={(e) => setField("scheme_type", e.target.value)}
              className={inputCls}
              placeholder="e.g. Financial Assistance, Insurance, Subsidy"
              aria-required="true"
            />
          </Field>

          <Field label="Benefits" required error={fieldErrors.benefits}>
            <textarea
              value={form.benefits}
              onChange={(e) => setField("benefits", e.target.value)}
              className={textareaCls}
              placeholder="What does the scheme provide?"
              aria-required="true"
            />
          </Field>

          <Field
            label="Application process"
            required
            error={fieldErrors.application_process}
          >
            <textarea
              value={form.application_process}
              onChange={(e) => setField("application_process", e.target.value)}
              className={textareaCls}
              placeholder="Steps to apply"
              aria-required="true"
            />
          </Field>

          <Field label="Official website" error={fieldErrors.official_website}>
            <input
              type="url"
              value={form.official_website ?? ""}
              onChange={(e) =>
                setField("official_website", e.target.value || null)
              }
              className={inputCls}
              placeholder="https://example.gov.in (optional)"
            />
          </Field>

          <Field label="Status">
            <label className="flex cursor-pointer items-center gap-2 text-sm text-slate-700">
              <input
                type="checkbox"
                checked={form.is_active}
                onChange={(e) => setField("is_active", e.target.checked)}
                className="h-4 w-4 rounded border-slate-300 text-emerald-600 focus:ring-emerald-500"
              />
              Active (visible to farmers)
            </label>
          </Field>
        </div>

        {/* Eligibility criteria */}
        <div className="mt-6 rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
          <div className="mb-4 flex items-center justify-between">
            <h2 className="text-base font-semibold text-slate-800">
              Eligibility Criteria
            </h2>
            <button
              type="button"
              onClick={addCriterion}
              className="rounded-lg border border-emerald-600 px-3 py-1.5 text-xs font-medium text-emerald-700 hover:bg-emerald-50"
            >
              + Add criterion
            </button>
          </div>

          {form.eligibility_criteria.length === 0 && (
            <p className="text-sm text-slate-500">
              No eligibility criteria. The scheme will be recommended to all farmers.
            </p>
          )}

          <div className="space-y-4">
            {form.eligibility_criteria.map((c, i) => (
              <div
                key={i}
                className="rounded-lg border border-slate-200 bg-slate-50 p-4"
              >
                <div className="mb-2 flex items-center justify-between">
                  <p className="text-xs font-semibold text-slate-600">
                    Criterion {i + 1}
                  </p>
                  <button
                    type="button"
                    onClick={() => removeCriterion(i)}
                    className="text-xs text-red-500 hover:text-red-700"
                    aria-label={`Remove criterion ${i + 1}`}
                  >
                    Remove
                  </button>
                </div>

                <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
                  <div>
                    <label className="mb-1 block text-xs font-medium text-slate-600">
                      Field name <span className="text-red-500">*</span>
                    </label>
                    <input
                      type="text"
                      value={c.field_name}
                      onChange={(e) =>
                        setCriterionField(i, "field_name", e.target.value)
                      }
                      className={inputCls}
                      placeholder="e.g. state, annual_income, primary_crop"
                    />
                    {fieldErrors[`criteria_${i}_field_name`] && (
                      <p className="mt-0.5 text-xs text-red-600">
                        {fieldErrors[`criteria_${i}_field_name`]}
                      </p>
                    )}
                  </div>

                  <div>
                    <label className="mb-1 block text-xs font-medium text-slate-600">
                      Operator <span className="text-red-500">*</span>
                    </label>
                    <select
                      value={c.operator}
                      onChange={(e) =>
                        setCriterionField(i, "operator", e.target.value)
                      }
                      className={inputCls}
                    >
                      {OPERATOR_OPTIONS.map((op) => (
                        <option key={op} value={op}>
                          {op}
                        </option>
                      ))}
                    </select>
                  </div>

                  <div>
                    <label className="mb-1 block text-xs font-medium text-slate-600">
                      Expected value <span className="text-red-500">*</span>
                    </label>
                    <input
                      type="text"
                      value={c.expected_value}
                      onChange={(e) =>
                        setCriterionField(i, "expected_value", e.target.value)
                      }
                      className={inputCls}
                      placeholder="e.g. Telangana"
                    />
                    {fieldErrors[`criteria_${i}_expected_value`] && (
                      <p className="mt-0.5 text-xs text-red-600">
                        {fieldErrors[`criteria_${i}_expected_value`]}
                      </p>
                    )}
                  </div>

                  <div>
                    <label className="mb-1 block text-xs font-medium text-slate-600">
                      Criterion type
                    </label>
                    <input
                      type="text"
                      value={c.criterion_type}
                      onChange={(e) =>
                        setCriterionField(i, "criterion_type", e.target.value)
                      }
                      className={inputCls}
                      placeholder="profile"
                    />
                  </div>

                  <div className="sm:col-span-2">
                    <label className="mb-1 block text-xs font-medium text-slate-600">
                      Description (optional)
                    </label>
                    <input
                      type="text"
                      value={c.description ?? ""}
                      onChange={(e) =>
                        setCriterionField(
                          i,
                          "description",
                          e.target.value || null,
                        )
                      }
                      className={inputCls}
                      placeholder="Human-readable explanation"
                    />
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Submit */}
        <div className="mt-6">
          {submitError && (
            <p
              className="mb-4 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700"
              role="alert"
            >
              {submitError}
            </p>
          )}

          <div className="flex items-center gap-3">
            <button
              type="submit"
              disabled={isSubmitting}
              className="rounded-lg bg-emerald-700 px-5 py-2 text-sm font-medium text-white hover:bg-emerald-800 disabled:opacity-50"
            >
              {isSubmitting
                ? isEdit
                  ? "Saving…"
                  : "Creating…"
                : isEdit
                  ? "Save changes"
                  : "Create scheme"}
            </button>
            <button
              type="button"
              onClick={() => navigate("/admin/schemes")}
              disabled={isSubmitting}
              className="rounded-lg border border-slate-300 px-5 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50 disabled:opacity-50"
            >
              Cancel
            </button>
          </div>
        </div>
      </form>
    </div>
  );
}
