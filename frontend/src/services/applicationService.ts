import api from "./api";
import type {
  ApplicationChecklist,
  ApplicationCreatePayload,
  ApplicationListResponse,
  ApplicationSummary,
  ApplicationUpdatePayload,
  FarmerSchemeApplication,
} from "../types/application";

export async function getApplications(): Promise<ApplicationListResponse> {
  const response = await api.get<ApplicationListResponse>("/api/applications");
  return response.data;
}

export async function getApplicationSummary(): Promise<ApplicationSummary> {
  const response = await api.get<ApplicationSummary>("/api/applications/summary");
  return response.data;
}

export async function createApplication(
  schemeId: number,
  data: ApplicationCreatePayload = {},
): Promise<FarmerSchemeApplication> {
  const response = await api.post<FarmerSchemeApplication>(
    `/api/schemes/${schemeId}/application`,
    data,
  );
  return response.data;
}

export async function getApplication(
  schemeId: number,
): Promise<FarmerSchemeApplication> {
  const response = await api.get<FarmerSchemeApplication>(
    `/api/schemes/${schemeId}/application`,
  );
  return response.data;
}

export async function updateApplication(
  schemeId: number,
  data: ApplicationUpdatePayload,
): Promise<FarmerSchemeApplication> {
  const response = await api.patch<FarmerSchemeApplication>(
    `/api/schemes/${schemeId}/application`,
    data,
  );
  return response.data;
}

export async function getApplicationChecklist(
  schemeId: number,
): Promise<ApplicationChecklist> {
  const response = await api.get<ApplicationChecklist>(
    `/api/schemes/${schemeId}/application/checklist`,
  );
  return response.data;
}
