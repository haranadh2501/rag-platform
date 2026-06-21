'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { deleteConversation, listConversations } from '../../lib/chat/chatApi';
import type { ConversationOut } from '../../../chat/types/chat';

interface ConversationListProps {
  activeConversationId?: string;
}

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' });
}

export default function ConversationList({ activeConversationId }: ConversationListProps) {
  const [conversations, setConversations] = useState<ConversationOut[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [hasError, setHasError] = useState(false);

  function load() {
    setIsLoading(true);
    setHasError(false);
    listConversations()
      .then((res) => setConversations(res.conversations))
      .catch(() => setHasError(true))
      .finally(() => setIsLoading(false));
  }

  useEffect(() => {
    load();
    // Re-fetch when a new conversation_id appears (e.g. after the first
    // message in /chat/new resolves) so its title shows up without a remount.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeConversationId]);

  async function handleDelete(id: string) {
    try {
      await deleteConversation(id);
      load();
    } catch {
      setHasError(true);
    }
  }

  return (
    <div className="flex flex-1 flex-col overflow-y-auto">
      <div className="px-4 py-3">
        <Link
          href="/chat/new"
          className="block rounded-md bg-[var(--accent-600)] px-3 py-2 text-center text-xs font-medium text-white hover:bg-[var(--accent-700)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent-600)] focus-visible:ring-offset-2"
        >
          New Chat
        </Link>
      </div>

      {isLoading && <p className="px-4 text-xs text-slate-400">Loading conversations…</p>}
      {!isLoading && hasError && (
        <p className="px-4 text-xs text-slate-400">We couldn&apos;t load your conversations. Please try again shortly.</p>
      )}
      {!isLoading && !hasError && conversations.length === 0 && (
        <p className="px-4 text-xs text-slate-400">Your conversations will appear here.</p>
      )}

      {!isLoading && !hasError && conversations.length > 0 && (
        <ul className="flex flex-col gap-0.5 px-2">
          {conversations.map((conversation) => {
            const isActive = conversation.id === activeConversationId;
            return (
              <li key={conversation.id} className="group flex items-center gap-1">
                <Link
                  href={`/chat/${conversation.id}`}
                  className={`flex-1 truncate rounded-md px-2 py-2 text-xs ${
                    isActive ? 'bg-[var(--accent-50)] text-[var(--accent-700)]' : 'text-slate-600 hover:bg-slate-50'
                  }`}
                >
                  <span className="block truncate font-medium">{conversation.title ?? 'Untitled conversation'}</span>
                  <span className="block text-[10px] text-slate-400">{formatDate(conversation.created_at)}</span>
                </Link>
                <button
                  type="button"
                  onClick={() => handleDelete(conversation.id)}
                  aria-label="Delete conversation"
                  className="shrink-0 rounded-md px-1.5 py-1 text-[10px] text-slate-400 opacity-0 hover:bg-red-50 hover:text-red-600 group-hover:opacity-100"
                >
                  ✕
                </button>
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}
