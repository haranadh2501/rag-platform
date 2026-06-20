import type { ChatMessageOut } from '../../../chat/types/chat';
import MessageBubble from './MessageBubble';

interface MessageListProps {
  messages: ChatMessageOut[];
}

export default function MessageList({ messages }: MessageListProps) {
  return (
    <div className="flex flex-1 flex-col gap-3 overflow-y-auto px-4 py-4">
      {messages.map((message) => (
        <MessageBubble key={message.id} message={message} />
      ))}
    </div>
  );
}
