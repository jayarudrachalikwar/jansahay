import api from "./api";
import type {
  AdminSchemeListResponse,
  AdminSchemePayload,
  AdminSchemeResponse,
} from "../types/adminScheme";

const BASE = "/api/admin/schemes";

export async function listAdminSchemes(): Promise<AdminSchemeListResponse> {
  const response = await api.get<AdminSchemeListResponse>(BASE);
  return response.data;
}

export async function getAdminScheme(schemeId: number): Promise<AdminSchemeResponse> {
  const response = await api.get<AdminSchemeResponse>(`${BASE}/${schemeId}`);
  return response.data;
}

export async function createAdminScheme(
  payload: AdminSchemePayload,
): Promise<AdminSchemeResponse> {
  const response = await api.post<AdminSchemeResponse>(BASE, payload);
  return response.data;
}

export async function updateAdminScheme(
  schemeId: number,
  payload: AdminSchemePayload,
): Promise<AdminSchemeResponse> {
  const response = await api.put<AdminSchemeResponse>(`${BASE}/${schemeId}`, payload);
  return response.data;
}

export async function deleteAdminScheme(schemeId: number): Promise<void> {
  await api.delete(`${BASE}/${schemeId}`);
}
