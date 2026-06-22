'use client';

import { useState } from 'react';
import { useSearchParams } from 'next/navigation';
import ChatAuthGuard from '../../../components/chat/ChatAuthGuard';
import ChatLayout from '../../../components/chat/ChatLayout';
import MessageList from '../../../components/chat/MessageList';
import MessageInput from '../../../components/chat/MessageInput';
import TypingIndicator from '../../../components/chat/TypingIndicator';
import ChatEmptyState from '../../../components/chat/ChatEmptyState';
import ChatErrorState from '../../../components/chat/ChatErrorState';
import FollowUpChips from '../../../components/chat/FollowUpChips';
import { sendQuery } from '../../../lib/chat/chatApi';
import type { ChatMessageOut, ChatQueryResponse } from '../../../../chat/types/chat';

function createMessageId(): string {
  if (typeof crypto !== 'undefined' && 'randomUUID' in crypto) {
    return crypto.randomUUID();
  }
  return `${Date.now()}-${Math.random().toString(36).slice(2)}`;
}

function NewChatDraft() {
  const [messages, setMessages] = useState<ChatMessageOut[]>([]);
  const [conversationId, setConversationId] = useState<string | null>(null);
  const [lastResponse, setLastResponse] = useState<ChatQueryResponse | null>(null);
  const [isSending, setIsSending] = useState(false);
  const [hasError, setHasError] = useState(false);
  const [pendingQuery, setPendingQuery] = useState<string | null>(null);

  async function runQuery(query: string) {
    setHasError(false);
    setPendingQuery(query);
    setIsSending(true);

    try {
      const response = await sendQuery({ query, conversation_id: conversationId });
      setConversationId(response.conversation_id);
      setLastResponse(response);
      setMessages((prev) => [
        ...prev,
        {
          id: createMessageId(),
          role: 'assistant',
          content: response.answer,
          sources: response.sources,
          faithfulness: response.faithfulness,
          requires_clarification: response.requires_clarification,
          created_at: new Date().toISOString(),
        },
      ]);
      setPendingQuery(null);
    } catch {
      setHasError(true);
    } finally {
      setIsSending(false);
    }
  }

  async function handleSend(query: string) {
    setMessages((prev) => [
      ...prev,
      {
        id: createMessageId(),
        role: 'user',
        content: query,
        sources: [],
        faithfulness: null,
        requires_clarification: false,
        created_at: new Date().toISOString(),
      },
    ]);
    await runQuery(query);
  }

  function handleRetry() {
    if (pendingQuery) {
      void runQuery(pendingQuery);
    }
  }

  const hasMessages = messages.length > 0;

  return (
    <ChatAuthGuard>
      <ChatLayout conversationId={conversationId ?? undefined}>
        <div className="flex flex-1 flex-col">
          {hasMessages ? <MessageList messages={messages} /> : <ChatEmptyState onSelectPrompt={handleSend} />}

          {lastResponse && hasMessages && (
            <div className="-mt-1 px-4 pb-4">
              <FollowUpChips questions={lastResponse.follow_up_questions} onSelect={handleSend} />
            </div>
          )}

          {isSending && <TypingIndicator />}
          {hasError && <ChatErrorState onRetry={handleRetry} />}

          <MessageInput onSubmit={handleSend} disabled={isSending} />
        </div>
      </ChatLayout>
    </ChatAuthGuard>
  );
}

export default function NewChatPage() {
  const searchParams = useSearchParams();
  // Clicking "New Chat" while already on /chat/new is otherwise a no-op
  // navigation (same URL), which left a finished draft's messages on
  // screen. ConversationList bumps `reset` on every click; keying on it
  // forces this component to remount with empty state instead of reusing
  // whatever draft/conversation was already in progress.
  return <NewChatDraft key={searchParams.get('reset') ?? 'initial'} />;
}
