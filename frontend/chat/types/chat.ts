/**
 * Chat Portal type contract (M9).
 * Derived from specs/openapi.yaml — that file is the source of truth.
 * This file IS the canonical type source for the Chat Portal.
 * Import directly from here; do not maintain a duplicate copy elsewhere.
 * No React. No side effects. Pure types and constants only.
 */

// ── Enums / Unions ────────────────────────────────────────────────────────────

export type ChatMessageRole = 'user' | 'assistant';

// ── API Response Shapes ───────────────────────────────────────────────────────

export interface SourceChunk {
  document_id: string;
  title: string;
  chunk_text: string;
  page_number: number | null;
  score: number;
}

export interface ChatQueryResponse {
  answer: string;
  sources: SourceChunk[];
  follow_up_questions: string[];
  conversation_id: string;
  /** Self-check / grounding score in [0, 1]; below threshold triggers a retry server-side. */
  faithfulness: number;
  requires_clarification: boolean;
  metadata: {
    model: string;
    retrieval_time_ms: number;
    chunks_retrieved: number;
  };
}

export interface ConversationOut {
  id: string;
  title: string | null;
  channel: string;
  created_at: string; // ISO 8601
  message_count: number;
}

export interface ChatMessageOut {
  id: string;
  role: ChatMessageRole;
  content: string;
  sources: SourceChunk[];
  faithfulness: number | null;
  requires_clarification: boolean;
  created_at: string; // ISO 8601
}

/**
 * GET /chat/conversations/{conversation_id} response.
 * openapi.yaml expresses this as an inline allOf [ConversationOut, { messages }]
 * rather than a named schema — defined here as its own interface for typed use.
 */
export interface ConversationDetail extends ConversationOut {
  messages: ChatMessageOut[];
}

/**
 * GET /chat/conversations response.
 * openapi.yaml expresses this as an inline object schema, not a named one.
 */
export interface ConversationListResponse {
  conversations: ConversationOut[];
}

// ── Request Shapes ────────────────────────────────────────────────────────────

/**
 * POST /chat/query request body.
 * There is no POST /chat/conversations endpoint — omit conversation_id (or
 * pass null) to start a new conversation; the backend creates it and returns
 * the new id in ChatQueryResponse.conversation_id.
 */
export interface ChatQueryRequest {
  query: string;
  conversation_id?: string | null;
  max_chunks?: number;
}
