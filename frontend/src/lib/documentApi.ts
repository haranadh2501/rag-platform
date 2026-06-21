import { apiRequest } from './apiClient';
import type { DocumentList, DocumentOut } from '@admin-types';

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
