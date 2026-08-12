// Admin scheme types — exact mirror of backend AdminSchemeCreate/Update/Response contracts.
// No enums: all fields are plain strings matching backend String columns.

export interface AdminEligibilityCriterion {
  id: number;
  criterion_type: string;
  field_name: string;
  operator: string;
  expected_value: string;
  description: string | null;
}

export interface AdminEligibilityCriterionInput {
  criterion_type: string;
  field_name: string;
  operator: string;
  expected_value: string;
  description: string | null;
}

export interface AdminSchemeResponse {
  id: number;
  name: string;
  short_description: string;
  detailed_description: string;
  department: string;
  state: string;
  scheme_type: string;
  benefits: string;
  application_process: string;
  official_website: string | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
  eligibility_criteria: AdminEligibilityCriterion[];
}

export interface AdminSchemeListResponse {
  schemes: AdminSchemeResponse[];
  total: number;
}

// Create and Update share the same shape (PUT = full replacement)
export interface AdminSchemePayload {
  name: string;
  short_description: string;
  detailed_description: string;
  department: string;
  state: string;
  scheme_type: string;
  benefits: string;
  application_process: string;
  official_website: string | null;
  is_active: boolean;
  eligibility_criteria: AdminEligibilityCriterionInput[];
}
