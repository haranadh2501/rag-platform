'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { usePathname, useSearchParams } from 'next/navigation';
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
  const pathname = usePathname();
  const searchParams = useSearchParams();

  // /chat/new renders this with no id until the first message resolves —
  // that's the only caller that omits the prop, so its absence unambiguously
  // means "draft, not yet a real conversation" (no fetch/persistence involved).
  const isDraft = activeConversationId === undefined;

  // A plain "/chat/new" href is a no-op click when we're already on that
  // exact URL (same-URL navigations don't fire), which is what left a
  // finished draft's old messages on screen. Bumping a query param forces a
  // real navigation — and therefore a fresh draft — every time.
  const newChatHref =
    pathname === '/chat/new' ? `/chat/new?reset=${Number(searchParams.get('reset') ?? '0') + 1}` : '/chat/new';

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
          href={newChatHref}
          className="block rounded-md bg-indigo-600 px-3 py-2 text-center text-xs font-medium text-white hover:bg-indigo-700 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-indigo-600 focus-visible:ring-offset-2"
        >
          New Chat
        </Link>
      </div>

      {isLoading && <p className="px-4 text-xs text-slate-400 dark:text-slate-500">Loading conversations…</p>}
      {!isLoading && hasError && (
        <p className="px-4 text-xs text-slate-400 dark:text-slate-500">We couldn&apos;t load your conversations. Please try again shortly.</p>
      )}
      {!isLoading && !hasError && !isDraft && conversations.length === 0 && (
        <p className="px-4 text-xs text-slate-400 dark:text-slate-500">Your conversations will appear here.</p>
      )}

      {!isLoading && !hasError && (isDraft || conversations.length > 0) && (
        <ul className="flex flex-col gap-0.5 px-2">
          {isDraft && (
            <li>
              <div className="block truncate rounded-md bg-slate-100 px-2 py-2 text-xs text-slate-800 dark:bg-slate-800 dark:text-slate-100">
                <span className="block truncate font-medium">New conversation</span>
                <span className="block text-[10px] text-slate-400 dark:text-slate-500">Draft</span>
              </div>
            </li>
          )}
          {conversations.map((conversation) => {
            const isActive = conversation.id === activeConversationId;
            return (
              <li key={conversation.id} className="group flex items-center gap-1">
                <Link
                  href={`/chat/${conversation.id}`}
                  className={`flex-1 truncate rounded-md px-2 py-2 text-xs ${
                    isActive
                      ? 'bg-slate-100 text-slate-800 dark:bg-slate-800 dark:text-slate-100'
                      : 'text-slate-600 hover:bg-slate-50 dark:text-slate-300 dark:hover:bg-slate-800/60'
                  }`}
                >
                  <span className="block truncate font-medium">{conversation.title ?? 'Untitled conversation'}</span>
                  <span className="block text-[10px] text-slate-400 dark:text-slate-500">{formatDate(conversation.created_at)}</span>
                </Link>
                <button
                  type="button"
                  onClick={() => handleDelete(conversation.id)}
                  aria-label="Delete conversation"
                  className="shrink-0 rounded-md px-1.5 py-1 text-[10px] text-slate-400 opacity-0 hover:bg-red-50 hover:text-red-600 group-hover:opacity-100 dark:text-slate-500 dark:hover:bg-red-950/40 dark:hover:text-red-400"
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
