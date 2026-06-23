'use client';

import { useState } from 'react';
import ChatThemeProvider from './ChatThemeProvider';
import ChatThemeToggle from './ChatThemeToggle';
import ConversationList from './ConversationList';

interface ChatLayoutProps {
  conversationId?: string;
  children?: React.ReactNode;
}

export default function ChatLayout({ conversationId, children }: ChatLayoutProps) {
  const [sidebarOpen, setSidebarOpen] = useState(false);

  return (
    <ChatThemeProvider>
      <div className="flex h-screen overflow-hidden bg-slate-50 dark:bg-slate-950">
        {sidebarOpen && (
          <div
            className="fixed inset-0 z-20 bg-slate-900/50 md:hidden"
            onClick={() => setSidebarOpen(false)}
            aria-hidden="true"
          />
        )}

        <aside
          className={[
            'fixed inset-y-0 left-0 z-30 flex w-60 shrink-0 flex-col bg-white shadow-sm transition-transform duration-200 ease-in-out dark:bg-slate-900',
            'md:static md:translate-x-0 md:border-r md:border-slate-200 md:shadow-none dark:md:border-slate-800',
            sidebarOpen ? 'translate-x-0' : '-translate-x-full',
          ].join(' ')}
        >
          <div className="flex h-16 shrink-0 items-center justify-between border-b border-slate-100 px-6 dark:border-slate-800">
            <span className="text-sm font-semibold tracking-wide text-indigo-600 dark:text-indigo-400">Chat</span>
            <div className="flex items-center gap-1">
              <ChatThemeToggle />
              <button
                type="button"
                onClick={() => setSidebarOpen(false)}
                aria-label="Close sidebar"
                className="rounded-md p-1 text-slate-400 hover:bg-slate-100 md:hidden dark:text-slate-500 dark:hover:bg-slate-800"
              >
                ✕
              </button>
            </div>
          </div>
          <ConversationList activeConversationId={conversationId} />
        </aside>

        <div className="flex flex-1 flex-col overflow-hidden">
          <div className="flex h-12 shrink-0 items-center gap-3 border-b border-slate-200 bg-white px-4 md:hidden dark:border-slate-800 dark:bg-slate-900">
            <button
              type="button"
              onClick={() => setSidebarOpen(true)}
              aria-label="Open sidebar"
              className="rounded-md p-1.5 text-slate-500 hover:bg-slate-100 dark:text-slate-400 dark:hover:bg-slate-800"
            >
              <svg className="h-5 w-5" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24" aria-hidden="true">
                <path strokeLinecap="round" strokeLinejoin="round" d="M3.75 6.75h16.5M3.75 12h16.5m-16.5 5.25h16.5" />
              </svg>
            </button>
            <span className="text-sm font-semibold text-slate-800 dark:text-slate-100">Chat</span>
          </div>

          <main className="flex flex-1 flex-col overflow-y-auto">
            {children ?? (
              <div className="flex flex-1 items-center justify-center text-sm text-slate-400 dark:text-slate-500">
                {conversationId ? `Conversation ${conversationId} placeholder` : 'New chat placeholder'}
              </div>
            )}
          </main>
        </div>
      </div>
    </ChatThemeProvider>
  );
}
