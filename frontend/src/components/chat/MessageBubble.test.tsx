import { describe, it, expect } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import MessageBubble from './MessageBubble';
import type { ChatMessageOut } from '../../../chat/types/chat';

describe('MessageBubble', () => {
  it('renders assistant citations from message.sources', () => {
    const message: ChatMessageOut = {
      id: '1',
      role: 'assistant',
      content: 'Here is the answer.',
      sources: [
        { document_id: 'doc-1', title: 'Manual', chunk_text: 'Relevant excerpt', page_number: 3, score: 0.91 },
      ],
      faithfulness: 0.9,
      requires_clarification: false,
      created_at: new Date().toISOString(),
    };

    render(<MessageBubble message={message} />);

    fireEvent.click(screen.getByText('1 source'));
    expect(screen.getByText('Relevant excerpt')).toBeInTheDocument();
  });

  it('does not render citations for a user message', () => {
    const message: ChatMessageOut = {
      id: '2',
      role: 'user',
      content: 'What is the warranty period?',
      sources: [],
      faithfulness: null,
      requires_clarification: false,
      created_at: new Date().toISOString(),
    };

    render(<MessageBubble message={message} />);

    expect(screen.queryByText('No citations available')).not.toBeInTheDocument();
  });

  it('renders the user bubble right-aligned, using the accent color token', () => {
    const message: ChatMessageOut = {
      id: '3',
      role: 'user',
      content: 'Hi there',
      sources: [],
      faithfulness: null,
      requires_clarification: false,
      created_at: new Date().toISOString(),
    };

    const { container } = render(<MessageBubble message={message} />);

    expect(container.firstElementChild).toHaveClass('justify-end');
    expect(screen.getByText('Hi there').className).toContain('bg-[var(--accent-600)]');
  });

  it('renders the assistant bubble left-aligned and neutral (no accent color)', () => {
    const message: ChatMessageOut = {
      id: '4',
      role: 'assistant',
      content: 'Here is the answer.',
      sources: [],
      faithfulness: 0.9,
      requires_clarification: false,
      created_at: new Date().toISOString(),
    };

    const { container } = render(<MessageBubble message={message} />);

    expect(container.firstElementChild).toHaveClass('items-start');
    const bubble = container.querySelector('.bg-white');
    expect(bubble).not.toBeNull();
    expect(bubble?.className).not.toContain('accent');
    expect(container.querySelector('[aria-hidden="true"]')?.className).toContain('bg-slate-100');
  });
});
