import api from "./api";
import type {
  FarmerProfile,
  FarmerProfilePayload,
  ProfileCompletion,
  ProfileCompletionDetail,
} from "../types/profile";

export async function getProfile(): Promise<FarmerProfile> {
  const response = await api.get<FarmerProfile>("/api/profile");
  return response.data;
}

export async function createProfile(
  data: FarmerProfilePayload,
): Promise<FarmerProfile> {
  const response = await api.post<FarmerProfile>("/api/profile", data);
  return response.data;
}

export async function updateProfile(
  data: FarmerProfilePayload,
): Promise<FarmerProfile> {
  const response = await api.put<FarmerProfile>("/api/profile", data);
  return response.data;
}

export async function getProfileCompletion(): Promise<ProfileCompletion> {
  const response = await api.get<ProfileCompletion>("/api/profile/completion");
  return response.data;
}

export async function getProfileCompletionDetail(): Promise<ProfileCompletionDetail> {
  const response = await api.get<ProfileCompletionDetail>(
    "/api/profile/completion/detail",
  );
  return response.data;
}
