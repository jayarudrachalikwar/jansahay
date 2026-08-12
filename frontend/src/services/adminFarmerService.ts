import api from "./api";
import type { AdminFarmerDetail, AdminFarmerListResponse } from "../types/adminFarmer";

export async function listFarmers(): Promise<AdminFarmerListResponse> {
  const response = await api.get<AdminFarmerListResponse>("/api/admin/farmers");
  return response.data;
}

export async function getFarmer(farmerId: number): Promise<AdminFarmerDetail> {
  const response = await api.get<AdminFarmerDetail>(`/api/admin/farmers/${farmerId}`);
  return response.data;
}
