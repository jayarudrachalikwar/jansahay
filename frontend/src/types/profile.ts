export interface FarmerProfile {
  id: number;
  user_id: number;
  date_of_birth: string | null;
  gender: string | null;
  state: string | null;
  district: string | null;
  village: string | null;
  land_size: number | null;
  land_unit: string | null;
  land_ownership: string | null;
  primary_crop: string | null;
  secondary_crop: string | null;
  soil_type: string | null;
  irrigation_type: string | null;
  farming_type: string | null;
  annual_income: number | null;
  created_at: string;
  updated_at: string;
}

export interface FarmerProfilePayload {
  date_of_birth?: string | null;
  gender?: string | null;
  state?: string | null;
  district?: string | null;
  village?: string | null;
  land_size?: number | null;
  land_unit?: string | null;
  land_ownership?: string | null;
  primary_crop?: string | null;
  secondary_crop?: string | null;
  soil_type?: string | null;
  irrigation_type?: string | null;
  farming_type?: string | null;
  annual_income?: number | null;
}

export interface ProfileCompletion {
  completion_percentage: number;
}

export interface ProfileCompletionField {
  field: string;
  label: string;
}

export interface ProfileCompletionDetail {
  completion_percentage: number;
  missing_fields: ProfileCompletionField[];
}
