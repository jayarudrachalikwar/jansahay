export interface Scheme {
  id: number;
  name: string;
  short_description: string;
  department: string;
  state: string;
  scheme_type: string;
  benefits: string;
}

export interface EligibilityCriterion {
  criterion_type: string;
  field_name: string;
  operator: string;
  expected_value: string;
  description: string | null;
}

export interface SchemeDetail extends Scheme {
  detailed_description: string;
  application_process: string;
  official_website: string | null;
  eligibility_criteria: EligibilityCriterion[];
}

export interface SchemeSearchResult {
  schemes: Scheme[];
  total: number;
}

export interface SchemeEligibilityResult {
  scheme: SchemeDetail;
  eligible: boolean;
  reasons: string[];
}

export type MatchStatus = "eligible" | "partial" | "no_match";

export interface SchemeRecommendation {
  scheme: Scheme;
  relevance_score: number;
  eligible: boolean;
  summary: string;
  factors: string[];
  match_status: MatchStatus;
}

export interface SchemeRecommendationsResult {
  recommendations: SchemeRecommendation[];
  total: number;
}

export interface SchemeFilters {
  search?: string;
  state?: string;
  scheme_type?: string;
}
