import ReactMarkdown from 'react-markdown';
import rehypeHighlight from 'rehype-highlight';
import type { Components } from 'react-markdown';
import type { ChatMessageOut } from '../../../chat/types/chat';
import ClarificationBanner from './ClarificationBanner';
import FaithfulnessBadge from './FaithfulnessBadge';
import CitationsPanel from './CitationsPanel';

interface MessageBubbleProps {
  message: ChatMessageOut;
}

const markdownComponents: Components = {
  a: ({ children, ...props }) => (
    <a {...props} target="_blank" rel="noreferrer" className="underline">
      {children}
    </a>
  ),
  code: ({ className, children, ...props }) => {
    if (className) {
      return (
        <code className={`font-mono text-xs ${className}`} {...props}>
          {children}
        </code>
      );
    }
    return (
      <code className="rounded bg-slate-100 px-1 py-0.5 font-mono text-xs text-slate-800 dark:bg-slate-700 dark:text-slate-100" {...props}>
        {children}
      </code>
    );
  },
  pre: ({ children, ...props }) => (
    <pre {...props} className="my-1 overflow-x-auto rounded-md bg-slate-900 p-3 text-xs text-slate-100">
      {children}
    </pre>
  ),
};

export default function MessageBubble({ message }: MessageBubbleProps) {
  const isUser = message.role === 'user';

  if (isUser) {
    return (
      <div className="flex justify-end">
        <div className="max-w-[85%] whitespace-pre-wrap break-words rounded-2xl rounded-br-md bg-indigo-600 px-4 py-2.5 text-sm text-white sm:max-w-[75%]">
          {message.content}
        </div>
      </div>
    );
  }

  return (
    <div className="flex items-start gap-3">
      <div
        aria-hidden="true"
        className="mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-slate-100 text-[11px] font-semibold text-slate-500 dark:bg-slate-700 dark:text-slate-300"
      >
        AI
      </div>
      <div className="flex max-w-[85%] flex-1 flex-col gap-2 sm:max-w-[80%]">
        <span className="text-xs font-medium text-slate-400 dark:text-slate-500">Assistant</span>
        <div className="break-words rounded-2xl rounded-bl-md border border-slate-200 bg-white px-4 py-3 text-sm leading-relaxed text-slate-800 shadow-sm dark:border-slate-700 dark:bg-slate-800 dark:text-slate-100">
          <ReactMarkdown rehypePlugins={[rehypeHighlight]} components={markdownComponents}>
            {message.content}
          </ReactMarkdown>
        </div>
        <div className="flex flex-col gap-2">
          <ClarificationBanner requiresClarification={message.requires_clarification} />
          <FaithfulnessBadge score={message.faithfulness} />
          <CitationsPanel sources={message.sources} />
        </div>
      </div>
    </div>
  );
}
