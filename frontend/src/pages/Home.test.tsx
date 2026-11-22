import { render, screen } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter } from 'react-router-dom';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import Home from './Home';
import { adaptersApi, collectionsApi, profilesApi, syncApi } from '../lib/api';
import { installsApi } from '../lib/setupApi';
import type { Collection, Profile, SyncStatus } from '../types';

vi.mock('../contexts/AuthContext', () => ({
  useAuth: () => ({ user: { id: 'user-1' } }),
}));

vi.mock('../lib/api', () => ({
  profilesApi: { list: vi.fn() },
  syncApi: { getStatus: vi.fn() },
  collectionsApi: { list: vi.fn(), listCommunity: vi.fn() },
  adaptersApi: { list: vi.fn() },
}));

vi.mock('../lib/setupApi', () => ({
  installsApi: { list: vi.fn() },
}));

const basePack: Collection = {
  id: 'pack-base',
  owner_id: 'starter-owner',
  name: 'Software Engineer',
  description: 'A starting point',
  git_url: '',
  git_branch: 'main',
  collection_type: 'base',
  visibility: 'public',
  is_active: true,
  artifact_count: 12,
  download_count: 1200,
  published: true,
  is_starter_pack: true,
  avg_rating: 4.8,
  rating_count: 10,
  moderation_status: 'approved',
  created_at: '2026-01-01T00:00:00Z',
  updated_at: '2026-01-01T00:00:00Z',
};

const addOnPack: Collection = {
  ...basePack,
  id: 'pack-addon',
  name: 'QA / Test Engineer',
  collection_type: 'additional',
  is_starter_pack: true,
};

const profile: Profile = {
  id: 'setup-1',
  owner_id: 'user-1',
  name: 'My software setup',
  base_collection_id: 'pack-base',
  additional_collection_ids: ['pack-addon'],
  disabled_artifact_ids: [],
  target_frameworks: ['claude-code', 'opencode'],
  is_public: false,
  version: 1,
  created_at: '2026-01-01T00:00:00Z',
  updated_at: '2026-01-01T00:00:00Z',
};

const syncRow = (overrides: Partial<SyncStatus> = {}): SyncStatus => ({
  id: 'sync-1',
  profile_id: 'setup-1',
  profile_name: 'My software setup',
  target: 'claude-code',
  machine_label: 'laptop',
  in_sync: true,
  locally_modified_files: [],
  last_checked_at: '2026-01-01T00:00:00Z',
  ...overrides,
});

function renderHome() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>
        <Home />
      </MemoryRouter>
    </QueryClientProvider>
  );
}

describe('Home', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(collectionsApi.list).mockResolvedValue([basePack, addOnPack]);
    vi.mocked(collectionsApi.listCommunity).mockResolvedValue({ items: [], total: 0 });
    vi.mocked(adaptersApi.list).mockResolvedValue([]);
    vi.mocked(profilesApi.list).mockResolvedValue([]);
    vi.mocked(syncApi.getStatus).mockResolvedValue([]);
    vi.mocked(installsApi.list).mockResolvedValue([]);
  });

  it('prompts a user with no setups to build their first one', async () => {
    renderHome();

    expect(await screen.findByText('Build your first setup')).toBeInTheDocument();
    expect(profilesApi.list).toHaveBeenCalledWith({ owner_id: 'user-1' });
    const cta = screen.getByRole('link', { name: /Start setup/i });
    expect(cta).toHaveAttribute('href', '/onboarding');
  });

  it('never treats another user\'s public profile as one of your setups', async () => {
    const publicProfile: Profile = {
      ...profile,
      id: 'public-setup',
      owner_id: 'user-2',
      name: 'Someone else\'s setup',
      is_public: true,
    };
    // Model a response that still contains a public profile owned by someone
    // else — Home must filter it out even if an older API ignores owner_id.
    vi.mocked(profilesApi.list).mockResolvedValue([publicProfile]);
    renderHome();

    expect(await screen.findByText('Build your first setup')).toBeInTheDocument();
    expect(screen.queryByText('Someone else\'s setup')).not.toBeInTheDocument();
  });

  it('tells a user with a setup but no sync reports to install it', async () => {
    vi.mocked(profilesApi.list).mockResolvedValue([profile]);
    renderHome();

    expect(await screen.findByText('Your setup is ready — install it')).toBeInTheDocument();
    expect(screen.getByRole('link', { name: /Install now/i })).toHaveAttribute(
      'href',
      '/setups/setup-1/install',
    );
  });

  it('renders setup cards with pack names and per-framework status', async () => {
    vi.mocked(profilesApi.list).mockResolvedValue([profile]);
    vi.mocked(syncApi.getStatus).mockResolvedValue([
      syncRow(),
      syncRow({ id: 'sync-2', target: 'opencode', in_sync: false }),
    ]);
    renderHome();

    expect(await screen.findByText('My software setup')).toBeInTheDocument();
    expect(screen.getByText('Software Engineer · QA / Test Engineer')).toBeInTheDocument();
    expect(screen.getByText('claude-code — verified')).toBeInTheDocument();
    expect(screen.getByText('opencode — not verified')).toBeInTheDocument();
    expect(screen.getByRole('link', { name: /New setup/i })).toHaveAttribute(
      'href',
      '/onboarding',
    );
  });

  it('shows an amber drift banner naming the setup and file count', async () => {
    vi.mocked(profilesApi.list).mockResolvedValue([profile]);
    vi.mocked(syncApi.getStatus).mockResolvedValue([
      syncRow({ in_sync: false, locally_modified_files: ['CLAUDE.md', 'AGENTS.md'] }),
    ]);
    renderHome();

    expect(
      await screen.findByText('My software setup: 2 changes since install'),
    ).toBeInTheDocument();
    expect(screen.getByRole('link', { name: /Review changes/i })).toHaveAttribute(
      'href',
      '/setups/setup-1',
    );
    expect(screen.getByText('claude-code — changed')).toBeInTheDocument();
  });

  it('aggregates drift honestly when rows span multiple setups', async () => {
    const secondSetup: Profile = { ...profile, id: 'setup-2', name: 'Second setup' };
    vi.mocked(profilesApi.list).mockResolvedValue([profile, secondSetup]);
    vi.mocked(syncApi.getStatus).mockResolvedValue([
      syncRow({ locally_modified_files: ['CLAUDE.md'] }),
      syncRow({
        id: 'sync-2',
        profile_id: 'setup-2',
        profile_name: 'Second setup',
        locally_modified_files: ['A', 'B', 'C'],
      }),
    ]);
    renderHome();

    expect(
      await screen.findByText('4 files changed across 2 setups'),
    ).toBeInTheDocument();
    expect(screen.getByRole('link', { name: /Review changes/i })).toHaveAttribute(
      'href',
      '/machine?tab=sync',
    );
  });

  it('shows a quiet healthy line when every sync row is clean', async () => {
    vi.mocked(profilesApi.list).mockResolvedValue([profile]);
    vi.mocked(syncApi.getStatus).mockResolvedValue([syncRow()]);
    renderHome();

    expect(
      await screen.findByText(/Every installed framework is in sync/),
    ).toBeInTheDocument();
  });

  it('renders recommended starter bundles and community highlights', async () => {
    vi.mocked(collectionsApi.listCommunity).mockResolvedValue({
      items: [
        { ...basePack, id: 'community-1', name: 'Rust Systems Engineer', is_starter_pack: false },
      ],
      total: 1,
    });
    renderHome();

    expect(await screen.findByText('Recommended packs')).toBeInTheDocument();
    expect(screen.getAllByText('Software Engineer').length).toBeGreaterThan(0);
    expect(screen.getByText('DevOps Engineer')).toBeInTheDocument();
    expect(screen.getByText('Data Scientist')).toBeInTheDocument();
    expect(screen.getByText('Vibecoder')).toBeInTheDocument();

    expect(await screen.findByText('Rust Systems Engineer')).toBeInTheDocument();
    expect(screen.getByRole('link', { name: /Rust Systems Engineer/ })).toHaveAttribute(
      'href',
      '/packs/community/community-1',
    );
  });

  it('filters starter packs out before slicing community highlights', async () => {
    vi.mocked(collectionsApi.listCommunity).mockResolvedValue({
      items: [
        { ...basePack, id: 'starter-1', name: 'Starter One' },
        { ...basePack, id: 'starter-2', name: 'Starter Two' },
        { ...basePack, id: 'starter-3', name: 'Starter Three' },
        { ...basePack, id: 'starter-4', name: 'Starter Four' },
        { ...basePack, id: 'community-real', name: 'Real Community Pack', is_starter_pack: false },
      ],
      total: 5,
    });
    renderHome();

    expect(await screen.findByText('Real Community Pack')).toBeInTheDocument();
    expect(screen.queryByText('Starter One')).not.toBeInTheDocument();
    expect(screen.queryByText('No community packs yet. Publish one of yours to start the shelf.')).not.toBeInTheDocument();
  });

  it('shows installed, not verified when a claim exists and no sync report does', async () => {
    vi.mocked(profilesApi.list).mockResolvedValue([profile]);
    vi.mocked(installsApi.list).mockImplementation(async (id: string) =>
      id === 'setup-1'
        ? [
            {
              id: 'claim-1',
              profile_id: 'setup-1',
              target: 'claude-code',
              location: 'machine',
              method: 'zip',
              created_at: '2026-01-01T00:00:00Z',
              updated_at: '2026-01-01T00:00:00Z',
            },
          ]
        : [],
    );

    renderHome();

    expect(await screen.findByText('Installed, not verified yet')).toBeInTheDocument();
    expect(screen.getByText('claude-code — installed, not verified')).toBeInTheDocument();
    expect(screen.getByText('opencode — not installed')).toBeInTheDocument();
  });

  it('keeps the single footer line with no object-count cards', async () => {
    renderHome();

    expect(
      await screen.findByText(/frameworks supported · MyACE v/),
    ).toBeInTheDocument();
    expect(screen.queryByText('Target Adapters')).not.toBeInTheDocument();
    expect(screen.queryByText('Quick Start')).not.toBeInTheDocument();
  });
});
