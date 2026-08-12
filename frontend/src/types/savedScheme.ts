import type { Scheme } from "./scheme";

export interface SavedScheme {
  id: number;
  scheme_id: number;
  saved_at: string;
  scheme: Scheme;
}

export interface SavedSchemeListResponse {
  saved_schemes: SavedScheme[];
  total: number;
}
