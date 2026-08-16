import { render, screen } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter } from 'react-router-dom';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import SyncDashboard from './SyncDashboard';

vi.mock('../lib/api', () => ({
  syncApi: {
    getStatus: vi.fn(),
  },
}));

import { syncApi } from '../lib/api';

function renderPage() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>
        <SyncDashboard />
      </MemoryRouter>
    </QueryClientProvider>
  );
}

const baseStatus = {
  id: 'status-1',
  profile_id: 'profile-1',
  profile_name: 'My Profile',
  target: 'claude-code',
  machine_label: 'laptop',
  last_checked_at: '2026-08-16T00:00:00Z',
};

describe('SyncDashboard', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('shows an empty state when nothing has been reported', async () => {
    (syncApi.getStatus as ReturnType<typeof vi.fn>).mockResolvedValue([]);
    renderPage();

    expect(await screen.findByText(/Nothing reported yet/i)).toBeInTheDocument();
  });

  it('renders an in-sync row', async () => {
    (syncApi.getStatus as ReturnType<typeof vi.fn>).mockResolvedValue([
      { ...baseStatus, in_sync: true, locally_modified_files: [] },
    ]);
    renderPage();

    expect(await screen.findByText('My Profile')).toBeInTheDocument();
    expect(screen.getByText('In sync')).toBeInTheDocument();
    expect(screen.getByText('laptop')).toBeInTheDocument();
  });

  it('renders a locally-modified row with its hint', async () => {
    (syncApi.getStatus as ReturnType<typeof vi.fn>).mockResolvedValue([
      { ...baseStatus, in_sync: false, locally_modified_files: ['CLAUDE.md'] },
    ]);
    renderPage();

    expect(await screen.findByText('Locally modified')).toBeInTheDocument();
    expect(screen.getByText(/Review your local edits/)).toBeInTheDocument();
  });

  it('renders a stale row (not in sync, no locally-modified files) with a pull hint', async () => {
    (syncApi.getStatus as ReturnType<typeof vi.fn>).mockResolvedValue([
      { ...baseStatus, in_sync: false, locally_modified_files: [] },
    ]);
    renderPage();

    expect(await screen.findByText('Stale')).toBeInTheDocument();
    expect(screen.getByText(/myace pull/)).toBeInTheDocument();
  });
});
