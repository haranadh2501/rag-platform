import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import CitationsPanel from './CitationsPanel';
import FollowUpChips from './FollowUpChips';

describe('CitationsPanel', () => {
  it('does not render fake citations when sources is empty', () => {
    render(<CitationsPanel sources={[]} />);
    expect(screen.getByText('No citations available')).toBeInTheDocument();
    expect(screen.queryByRole('button')).not.toBeInTheDocument();
  });
});

describe('FollowUpChips', () => {
  const questions = ['Q1', 'Q2', 'Q3', 'Q4'];

  it('renders at most 3 chips', () => {
    render(<FollowUpChips questions={questions} onSelect={() => {}} />);
    expect(screen.getAllByRole('button')).toHaveLength(3);
  });

  it('calls onSelect with the clicked question', () => {
    const onSelect = vi.fn();
    render(<FollowUpChips questions={questions} onSelect={onSelect} />);
    fireEvent.click(screen.getByText('Q2'));
    expect(onSelect).toHaveBeenCalledWith('Q2');
  });
});
