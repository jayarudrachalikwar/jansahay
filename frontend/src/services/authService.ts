import api, { setAuthToken } from "./api";
import type {
  LoginPayload,
  RegisterPayload,
  TokenResponse,
  User,
} from "../types/auth";

export async function registerUser(
  payload: RegisterPayload,
): Promise<TokenResponse> {
  const response = await api.post<TokenResponse>(
    "/api/auth/register",
    payload,
  );

  return response.data;
}

export async function loginUser(
  payload: LoginPayload,
): Promise<TokenResponse> {
  const response = await api.post<TokenResponse>(
    "/api/auth/login",
    payload,
  );

  return response.data;
}

export function persistToken(token: string | null): void {
  if (token) {
    localStorage.setItem("jansahay_token", token);
    setAuthToken(token);
    return;
  }

  localStorage.removeItem("jansahay_token");
  setAuthToken(null);
}

export async function getCurrentUser(): Promise<User> {
  const response = await api.get<User>("/api/auth/me");
  return response.data;
}

export function logoutUser(): void {
  localStorage.removeItem("jansahay_token");
  setAuthToken(null);
}

export function getStoredToken(): string | null {
  return localStorage.getItem("jansahay_token");
}