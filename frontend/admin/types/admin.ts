/**
 * Admin Portal type contract (M8).
 * Derived from specs/openapi.yaml — that file is the source of truth.
 * This file IS the canonical type source for the Admin Portal.
 * Import directly from here; do not maintain a duplicate copy elsewhere.
 * No React. No side effects. Pure types and constants only.
 */

// ── Enums / Unions ────────────────────────────────────────────────────────────

export type DocumentStatus = 'pending' | 'processing' | 'completed' | 'failed';

export type DocumentSourceType = 'pdf' | 'docx' | 'txt' | 'url';

export type UserRole = 'super_admin' | 'admin' | 'user';

export type Plan = 'free' | 'pro' | 'enterprise';

/**
 * Ordered pipeline stages executed by n8n during document ingestion.
 * The frontend only reads and displays these — it never drives them.
 */
export type IngestionStage =
  | 'uploaded'
  | 'validated'
  | 'parsed_ocr'
  | 'chunked'
  | 'embedded'
  | 'stored';

// ── API Response Shapes ───────────────────────────────────────────────────────

export interface DocumentOut {
  id: string;
  tenant_id: string;
  title: string;
  source_type: DocumentSourceType;
  source_url: string | null;
  status: DocumentStatus;
  chunk_count: number;
  error_message: string | null;
  // TODO: backend/openapi should expose failed_stage for precise failed pipeline rendering.
  // Track at: backend/app/api/admin.py + specs/openapi.yaml DocumentOut schema.
  failed_stage?: IngestionStage;
  created_at: string; // ISO 8601
}

export interface DocumentList {
  documents: DocumentOut[];
  total: number;
}

export interface UserOut {
  id: string;
  email: string;
  role: UserRole;
  tenant_id: string;
  is_active: boolean;
  created_at: string; // ISO 8601
}

export interface UserList {
  users: UserOut[];
  total: number;
}

export interface TenantOut {
  id: string;
  name: string;
  slug: string;
  plan: Plan;
  is_active: boolean;
  created_at: string; // ISO 8601
}

export interface TenantList {
  tenants: TenantOut[];
  total: number;
}

// ── Request Shapes ────────────────────────────────────────────────────────────

export interface UrlIngestRequest {
  url: string;
  title?: string;
}

/** Used by POST /admin/users/invite */
export interface InviteUserRequest {
  email: string;
  password: string;
  tenant_id: string;
  role?: Extract<UserRole, 'admin' | 'user'>;
}

export interface TenantCreate {
  name: string;
  slug: string;
  plan?: Plan;
}

export interface TenantPatch {
  name?: string;
  is_active?: boolean;
  plan?: Plan;
}

// ── Ingestion Pipeline Stepper ────────────────────────────────────────────────

/**
 * Ordered stages for the row-expand stepper on the Documents page.
 * Index position is used by PipelineState.activeIndex and failedIndex.
 */
export const INGESTION_STAGES: IngestionStage[] = [
  'uploaded',
  'validated',
  'parsed_ocr',
  'chunked',
  'embedded',
  'stored',
];

/**
 * Derived client-side view model for the stage stepper.
 *
 * activeIndex: index into INGESTION_STAGES of the currently running stage.
 *   -1 = not yet started; INGESTION_STAGES.length = all stages complete.
 *
 * failedIndex: index of the stage that failed, or null.
 *   Resolved from DocumentOut.failed_stage when present (precise);
 *   falls back to the last known active stage when absent (approximate).
 */
export interface PipelineState {
  activeIndex: number;
  failedIndex: number | null;
  errorMessage: string | null;
  chunkCount: number | null;
  indexedAt: string | null; // ISO 8601; set only when status === 'completed'
}

/**
 * Maps a DocumentOut to a PipelineState for the stepper component.
 * All transitions are driven by backend-reported status — never inferred
 * from frontend actions.
 */
export function pipelineStateFromDocument(doc: DocumentOut): PipelineState {
  switch (doc.status) {
    case 'pending':
      return { activeIndex: 0, failedIndex: null, errorMessage: null, chunkCount: null, indexedAt: null };
    case 'processing':
      // parsed_ocr (index 2) is the long-running n8n stage; shown as active.
      return { activeIndex: 2, failedIndex: null, errorMessage: null, chunkCount: null, indexedAt: null };
    case 'completed':
      return { activeIndex: INGESTION_STAGES.length, failedIndex: null, errorMessage: null, chunkCount: doc.chunk_count, indexedAt: doc.created_at };
    case 'failed': {
      const failedIndex = doc.failed_stage
        ? INGESTION_STAGES.indexOf(doc.failed_stage)
        : 2; // fallback: parsed_ocr (index 2) until backend exposes failed_stage
      return { activeIndex: failedIndex, failedIndex, errorMessage: doc.error_message, chunkCount: null, indexedAt: null };
    }
  }
}
