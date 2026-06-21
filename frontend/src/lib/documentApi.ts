import { apiRequest, ApiError, getAuthToken } from './apiClient';
import type { DocumentList, DocumentOut } from '@admin-types';

// Same base URL approach as apiClient.ts — NEXT_PUBLIC_API_URL, never hardcoded.
const BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000';

export interface IngestDocumentUrlParams {
  url: string;
  title?: string;
}

export async function ingestDocumentUrlApi(
  params: IngestDocumentUrlParams,
): Promise<DocumentOut> {
  return apiRequest<DocumentOut>('POST', '/admin/documents/url', params);
}

export interface ListDocumentsParams {
  page: number;
  perPage: number;
}

export async function listDocumentsApi({
  page,
  perPage,
}: ListDocumentsParams): Promise<DocumentList> {
  return apiRequest<DocumentList>(
    'GET',
    `/admin/documents?page=${page}&per_page=${perPage}`,
  );
}

export async function getDocumentApi(documentId: string): Promise<DocumentOut> {
  return apiRequest<DocumentOut>('GET', `/admin/documents/${documentId}`);
}

export interface UploadDocumentParams {
  file: File;
  title?: string;
  onProgress?: (percent: number) => void;
}

/**
 * Uploads a document file via XMLHttpRequest (not fetch/apiRequest) so upload
 * progress events are available. Bearer token comes from the same in-memory
 * store apiClient uses — no hardcoded JWT.
 */
export function uploadDocumentApi({
  file,
  title,
  onProgress,
}: UploadDocumentParams): Promise<DocumentOut> {
  const formData = new FormData();
  formData.append('file', file);
  if (title) {
    formData.append('title', title);
  }

  return new Promise<DocumentOut>((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    xhr.open('POST', `${BASE_URL}/admin/documents/upload`);

    const token = getAuthToken();
    if (token) {
      xhr.setRequestHeader('Authorization', `Bearer ${token}`);
    }

    if (onProgress) {
      xhr.upload.onprogress = (event) => {
        if (event.lengthComputable) {
          onProgress(Math.round((event.loaded / event.total) * 100));
        }
      };
    }

    xhr.onload = () => {
      if (xhr.status >= 200 && xhr.status < 300) {
        try {
          resolve(JSON.parse(xhr.responseText) as DocumentOut);
        } catch {
          reject(new ApiError(xhr.status, 'Invalid response from server'));
        }
        return;
      }
      let message = `HTTP ${xhr.status}`;
      try {
        const body = JSON.parse(xhr.responseText) as { detail?: unknown };
        if (typeof body?.detail === 'string') {
          message = body.detail;
        }
      } catch {
        // Response body unreadable — keep the default message.
      }
      reject(new ApiError(xhr.status, message));
    };

    xhr.onerror = () => {
      reject(new Error('Network error while uploading file'));
    };

    xhr.send(formData);
  });
}
