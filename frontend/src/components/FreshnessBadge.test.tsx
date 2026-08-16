import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import { FreshnessBadge, isFreshnessStale } from './FreshnessBadge';

describe('FreshnessBadge', () => {
  it('renders "Not yet verified" when last_verified_at is null', () => {
    render(<FreshnessBadge lastVerifiedAt={null} />);
    expect(screen.getByText('Not yet verified')).toBeInTheDocument();
  });

  it('renders "Verified {date}" for a recent verification', () => {
    const today = new Date().toISOString().slice(0, 10);
    render(<FreshnessBadge lastVerifiedAt={today} />);
    expect(screen.getByText(`Verified ${today}`)).toBeInTheDocument();
  });

  it('renders "Needs re-check" once past the threshold', () => {
    const oldDate = new Date(Date.now() - 200 * 24 * 60 * 60 * 1000).toISOString().slice(0, 10);
    render(<FreshnessBadge lastVerifiedAt={oldDate} />);
    expect(screen.getByText('Needs re-check')).toBeInTheDocument();
  });
});

describe('isFreshnessStale', () => {
  it('treats null/undefined as stale', () => {
    expect(isFreshnessStale(null)).toBe(true);
    expect(isFreshnessStale(undefined)).toBe(true);
  });

  it('treats a date within the threshold as fresh', () => {
    const recent = new Date(Date.now() - 5 * 24 * 60 * 60 * 1000).toISOString().slice(0, 10);
    expect(isFreshnessStale(recent)).toBe(false);
  });

  it('treats a date past the threshold as stale', () => {
    const old = new Date(Date.now() - 181 * 24 * 60 * 60 * 1000).toISOString().slice(0, 10);
    expect(isFreshnessStale(old)).toBe(true);
  });
});
