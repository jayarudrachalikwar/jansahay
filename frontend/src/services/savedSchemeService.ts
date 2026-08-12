import api from "./api";
import type { SavedScheme, SavedSchemeListResponse } from "../types/savedScheme";

export async function saveScheme(schemeId: number): Promise<SavedScheme> {
  const response = await api.post<SavedScheme>(`/api/schemes/${schemeId}/save`);
  return response.data;
}

export async function unsaveScheme(schemeId: number): Promise<void> {
  await api.delete(`/api/schemes/${schemeId}/save`);
}

export async function listSavedSchemes(): Promise<SavedSchemeListResponse> {
  const response = await api.get<SavedSchemeListResponse>("/api/saved-schemes");
  return response.data;
}
