import { apiRequest } from './apiClient';
import type { DocumentOut } from '@admin-types';

export interface IngestDocumentUrlParams {
  url: string;
  title?: string;
}

export async function ingestDocumentUrlApi(
  params: IngestDocumentUrlParams,
): Promise<DocumentOut> {
  return apiRequest<DocumentOut>('POST', '/admin/documents/url', params);
}
