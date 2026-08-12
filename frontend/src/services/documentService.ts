import api from "./api";
import type {
  DocumentChunkStats,
  DocumentListResponse,
  DocumentStatusUpdateRequest,
  GovernmentDocument,
  KnowledgeBaseStats,
} from "../types/document";

export interface ListDocumentsParams {
  status?: string;
  search?: string;
}

export async function listDocuments(
  params?: ListDocumentsParams,
): Promise<DocumentListResponse> {
  const response = await api.get<DocumentListResponse>("/api/admin/documents", {
    params: {
      ...(params?.status ? { status: params.status } : {}),
      ...(params?.search ? { search: params.search } : {}),
    },
  });
  return response.data;
}

export async function getDocument(documentId: number): Promise<GovernmentDocument> {
  const response = await api.get<GovernmentDocument>(
    `/api/admin/documents/${documentId}`,
  );
  return response.data;
}

export async function uploadDocument(file: File): Promise<GovernmentDocument> {
  const formData = new FormData();
  formData.append("file", file);
  const response = await api.post<GovernmentDocument>(
    "/api/admin/documents",
    formData,
    { headers: { "Content-Type": "multipart/form-data" } },
  );
  return response.data;
}

export async function updateDocumentStatus(
  documentId: number,
  payload: DocumentStatusUpdateRequest,
): Promise<GovernmentDocument> {
  const response = await api.patch<GovernmentDocument>(
    `/api/admin/documents/${documentId}/status`,
    payload,
  );
  return response.data;
}

export async function ingestDocument(documentId: number): Promise<GovernmentDocument> {
  const response = await api.post<GovernmentDocument>(
    `/api/admin/documents/${documentId}/ingest`,
  );
  return response.data;
}

export async function deleteDocument(documentId: number): Promise<void> {
  await api.delete(`/api/admin/documents/${documentId}`);
}

export async function getDocumentChunks(
  documentId: number,
): Promise<DocumentChunkStats> {
  const response = await api.get<DocumentChunkStats>(
    `/api/admin/documents/${documentId}/chunks`,
  );
  return response.data;
}

export async function getKnowledgeBaseStats(): Promise<KnowledgeBaseStats> {
  const response = await api.get<KnowledgeBaseStats>(
    "/api/admin/knowledge-base/stats",
  );
  return response.data;
}
