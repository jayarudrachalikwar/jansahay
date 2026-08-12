import type { Scheme } from "./scheme";

export type ApplicationStatus =
  | "not_started"
  | "preparing"
  | "ready_to_apply"
  | "submitted";

export interface FarmerSchemeApplication {
  id: number;
  user_id: number;
  scheme_id: number;
  status: ApplicationStatus;
  notes: string | null;
  created_at: string;
  updated_at: string;
  scheme: Scheme;
}

export interface ApplicationListResponse {
  applications: FarmerSchemeApplication[];
  total: number;
}

export interface ApplicationCreatePayload {
  notes?: string | null;
}

export interface ApplicationUpdatePayload {
  status?: ApplicationStatus;
  notes?: string | null;
}

export type ChecklistItemStatus = "complete" | "missing" | "attention";

export interface ApplicationChecklistItem {
  key: string;
  label: string;
  status: ChecklistItemStatus;
  message: string;
}

export interface ApplicationChecklist {
  items: ApplicationChecklistItem[];
  total: number;
  completed: number;
  missing: number;
  ready: boolean;
}

export interface ApplicationSummary {
  total: number;
  preparing: number;
  ready_to_apply: number;
  submitted: number;
}
