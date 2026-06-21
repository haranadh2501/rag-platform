import { describe, it, expect, vi } from 'vitest';
import { render, waitFor } from '@testing-library/react';
import ConversationList from './ConversationList';
import { listConversations } from '../../lib/chat/chatApi';

vi.mock('../../lib/chat/chatApi', () => ({
  listConversations: vi.fn(),
  deleteConversation: vi.fn(),
}));

describe('ConversationList', () => {
  it('refetches when activeConversationId changes, e.g. after the first response of a new chat', async () => {
    vi.mocked(listConversations).mockResolvedValue({ conversations: [] });

    const { rerender } = render(<ConversationList activeConversationId={undefined} />);
    await waitFor(() => expect(listConversations).toHaveBeenCalledTimes(1));

    rerender(<ConversationList activeConversationId="conv-1" />);
    await waitFor(() => expect(listConversations).toHaveBeenCalledTimes(2));
  });
});
