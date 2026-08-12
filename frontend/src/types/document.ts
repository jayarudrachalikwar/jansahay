export type DocumentStatus = "uploaded" | "processing" | "indexed" | "failed" | "inactive";

export interface GovernmentDocument {
  id: number;
  filename: string;
  original_filename: string;
  content_type: string;
  file_size: number;
  page_count: number | null;
  document_id: string;
  status: DocumentStatus;
  error_message: string | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
  ingested_at: string | null;
}

export interface DocumentListResponse {
  documents: GovernmentDocument[];
  total: number;
}

export interface DocumentStatusUpdateRequest {
  is_active: boolean;
}

export interface DocumentChunkStats {
  document_id: string;
  chunk_count: number;
  collection_total: number;
}

export interface KnowledgeBaseStats {
  total_documents: number;
  by_status: Record<DocumentStatus, number>;
  total_indexed_chunks: number;
  qdrant_reachable: boolean;
}
