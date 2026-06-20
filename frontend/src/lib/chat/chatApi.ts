/**
 * Chat API helpers for the Chat Portal (M9).
 * Source of truth: specs/openapi.yaml.
 *
 * There is no POST /chat/conversations endpoint. A new conversation is
 * created implicitly by the backend when conversation_id is omitted/null on
 * POST /chat/query — the response's conversation_id is the newly created id.
 */

import { apiRequest } from '../apiClient';
import type {
  ChatQueryRequest,
  ChatQueryResponse,
  ConversationDetail,
  ConversationListResponse,
} from '../../../chat/types/chat';

/**
 * POST /chat/query
 * Pass conversation_id: null (or omit it) to start a new conversation.
 */
export async function sendQuery(request: ChatQueryRequest): Promise<ChatQueryResponse> {
  return apiRequest<ChatQueryResponse>('POST', '/chat/query', request);
}

/** GET /chat/conversations — list conversations for the current user. */
export async function listConversations(): Promise<ConversationListResponse> {
  return apiRequest<ConversationListResponse>('GET', '/chat/conversations');
}

/** GET /chat/conversations/{conversation_id} — header + embedded messages. */
export async function getConversation(conversationId: string): Promise<ConversationDetail> {
  return apiRequest<ConversationDetail>('GET', `/chat/conversations/${conversationId}`);
}

/** DELETE /chat/conversations/{conversation_id} */
export async function deleteConversation(conversationId: string): Promise<void> {
  return apiRequest<void>('DELETE', `/chat/conversations/${conversationId}`);
}
