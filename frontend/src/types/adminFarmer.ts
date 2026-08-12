export interface AdminFarmerProfile {
  id: number;
  date_of_birth: string | null;
  gender: string | null;
  state: string | null;
  district: string | null;
  village: string | null;
  land_size: string | null;
  land_unit: string | null;
  land_ownership: string | null;
  primary_crop: string | null;
  secondary_crop: string | null;
  soil_type: string | null;
  irrigation_type: string | null;
  farming_type: string | null;
  annual_income: string | null;
  created_at: string;
  updated_at: string;
}

export interface AdminFarmerListItem {
  id: number;
  full_name: string;
  email: string;
  phone_number: string | null;
  is_active: boolean;
  created_at: string;
  state: string | null;
  primary_crop: string | null;
  has_profile: boolean;
}

export interface AdminFarmerDetail {
  id: number;
  full_name: string;
  email: string;
  phone_number: string | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
  farmer_profile: AdminFarmerProfile | null;
}

export interface AdminFarmerListResponse {
  farmers: AdminFarmerListItem[];
  total: number;
}
