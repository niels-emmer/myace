import { render, screen, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter } from 'react-router-dom';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import CollectionDetail from './CollectionDetail';
import ProfileDetail from './ProfileDetail';

// Regression test for AGENTS.md rule 12: CollectionDetail (include_disabled:
// true) and ProfileDetail (include_disabled: false) fetch the same
// collection's artifacts. They used to share the bare ['artifacts', id] key,
// so whichever page loaded second rendered the other's cached rows.
let routeId = 'c1';
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom');
  return { ...actual, useParams: () => ({ id: routeId }), useNavigate: () => vi.fn() };
});

vi.mock('../lib/api', () => ({
  collectionsApi: { get: vi.fn(), getArtifacts: vi.fn(), list: vi.fn() },
  profilesApi: { get: vi.fn() },
  adaptersApi: { list: vi.fn() },
}));

import { collectionsApi, profilesApi, adaptersApi } from '../lib/api';

const artifact = (id: string, enabled: boolean) => ({
  id, collection_id: 'c1', artifact_type: 'rule', name: id, version: '1.0.0', priority: 50,
  target_compatibility: [], tags: [], description: '', body: 'b', file_path: 'AGENTS.md',
  is_enabled: enabled, created_at: '2025-01-01T00:00:00Z', updated_at: '2025-01-01T00:00:00Z',
});

describe('artifact query keys', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    (collectionsApi.get as ReturnType<typeof vi.fn>).mockResolvedValue({
      id: 'c1', owner_id: 'u', name: 'C1', description: '', git_url: 'x', git_branch: 'main',
      collection_type: 'base', visibility: 'private', is_active: true, artifact_count: 2,
      published: false, moderation_status: 'draft',
    });
    (collectionsApi.list as ReturnType<typeof vi.fn>).mockResolvedValue([]);
    (collectionsApi.getArtifacts as ReturnType<typeof vi.fn>).mockImplementation(
      async (_id: string, opts?: { include_disabled?: boolean }) =>
        opts?.include_disabled
          ? [artifact('on', true), artifact('off', false)]
          : [artifact('on', true)],
    );
    (profilesApi.get as ReturnType<typeof vi.fn>).mockResolvedValue({
      id: 'p1', owner_id: 'u', name: 'P', description: '', base_collection_id: 'c1',
      additional_collection_ids: [], disabled_artifact_ids: [], target_framework: 'claude-code',
      is_public: false, created_at: '2025-01-01T00:00:00Z', updated_at: '2025-01-01T00:00:00Z',
    });
    (adaptersApi.list as ReturnType<typeof vi.fn>).mockResolvedValue([]);
  });

  it('keeps the include_disabled and enabled-only fetches in separate cache entries', async () => {
    const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    const wrap = (ui: React.ReactNode) => (
      <QueryClientProvider client={queryClient}>
        <MemoryRouter>{ui}</MemoryRouter>
      </QueryClientProvider>
    );

    routeId = 'c1';
    const first = render(wrap(<CollectionDetail />));
    await screen.findAllByText('off');
    first.unmount();

    routeId = 'p1';
    render(wrap(<ProfileDetail />));
    await waitFor(() => {
      const keys = queryClient
        .getQueryCache()
        .findAll({ queryKey: ['artifacts', 'c1'] })
        .map((q) => JSON.stringify(q.queryKey));
      expect(keys).toHaveLength(2);
    });

    const withDisabled = queryClient.getQueryData<unknown[]>([
      'artifacts', 'c1', { include_disabled: true },
    ]);
    const enabledOnly = queryClient.getQueryData<unknown[]>([
      'artifacts', 'c1', { include_disabled: false },
    ]);
    expect(withDisabled).toHaveLength(2);
    expect(enabledOnly).toHaveLength(1);
  });
});
