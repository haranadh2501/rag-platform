import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import FaithfulnessBadge from './FaithfulnessBadge';

describe('FaithfulnessBadge', () => {
  it('renders Grounded for score >= 0.85', () => {
    render(<FaithfulnessBadge score={0.9} />);
    expect(screen.getByText(/^● Grounded/)).toBeInTheDocument();
  });

  it('renders Partially grounded for score between 0.70 and 0.84', () => {
    render(<FaithfulnessBadge score={0.75} />);
    expect(screen.getByText(/^● Partially grounded/)).toBeInTheDocument();
  });

  it('renders Low confidence for score below 0.70', () => {
    render(<FaithfulnessBadge score={0.5} />);
    expect(screen.getByText(/^● Low confidence/)).toBeInTheDocument();
  });

  it('renders Not scored when score is null', () => {
    render(<FaithfulnessBadge score={null} />);
    expect(screen.getByText(/^● Not scored/)).toBeInTheDocument();
  });
});
