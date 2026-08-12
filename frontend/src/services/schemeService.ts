import api from "./api";
import type {
  SchemeDetail,
  SchemeEligibilityResult,
  SchemeFilters,
  SchemeRecommendationsResult,
  SchemeSearchResult,
} from "../types/scheme";

export async function listSchemes(filters: SchemeFilters = {}): Promise<SchemeSearchResult> {
  const response = await api.get<SchemeSearchResult>("/api/schemes", { params: filters });
  return response.data;
}

export async function getScheme(schemeId: number): Promise<SchemeDetail> {
  const response = await api.get<SchemeDetail>(`/api/schemes/${schemeId}`);
  return response.data;
}

export async function checkSchemeEligibility(schemeId: number): Promise<SchemeEligibilityResult> {
  const response = await api.get<SchemeEligibilityResult>(`/api/schemes/${schemeId}/eligibility`);
  return response.data;
}

export async function getSchemeRecommendations(): Promise<SchemeRecommendationsResult> {
  const response = await api.get<SchemeRecommendationsResult>("/api/schemes/recommendations");
  return response.data;
}
