import api from "./api";
import type { SchemeRecommendationsResult } from "../types/scheme";

export type RecommendationSortBy = "score" | "name" | "eligibility";

export interface RecommendationParams {
  limit?: number;
  sort_by?: RecommendationSortBy;
  eligible_only?: boolean;
  scheme_type?: string;
  state?: string;
}

export async function getRecommendations(
  limit?: number,
  extraParams?: Omit<RecommendationParams, "limit">,
): Promise<SchemeRecommendationsResult> {
  const params: Record<string, string | number | boolean> = {};
  if (limit !== undefined) params.limit = limit;
  if (extraParams?.sort_by) params.sort_by = extraParams.sort_by;
  if (extraParams?.eligible_only !== undefined) params.eligible_only = extraParams.eligible_only;
  if (extraParams?.scheme_type) params.scheme_type = extraParams.scheme_type;
  if (extraParams?.state) params.state = extraParams.state;

  const response = await api.get<SchemeRecommendationsResult>("/api/recommendations", {
    params: Object.keys(params).length > 0 ? params : undefined,
  });
  return response.data;
}

export async function getRecommendationsSummary(): Promise<SchemeRecommendationsResult> {
  const response = await api.get<SchemeRecommendationsResult>("/api/recommendations/summary");
  return response.data;
}
