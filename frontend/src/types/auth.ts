export interface User {
  id: number;
  full_name: string;
  email: string;
  phone_number: string | null;
  role: "farmer" | "admin";
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
}

export interface RegisterPayload {
  full_name: string;
  email: string;
  phone_number?: string;
  password: string;
}

export interface LoginPayload {
  email: string;
  password: string;
}
