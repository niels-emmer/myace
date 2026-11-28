import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import PackDetail from './PackDetail';
import { adaptersApi, collectionsApi, commentsApi, profilesApi, ratingsApi } from '../lib/api';
import { packApi } from '../lib/packApi';
import { packUsageApi, setupProfilesApi } from '../lib/setupApi';
import type { Collection } from '../types';

let mockUser: { id: string; role: 'user' | 'moderator' | 'admin' } | null = null;

vi.mock('../contexts/AuthContext', () => ({
  useAuth: () => ({ user: mockUser, isLoading: false }),
}));

vi.mock('../lib/api', () => ({
  adaptersApi: { list: vi.fn() },
  collectionsApi: {
    get: vi.fn(),
    getArtifacts: vi.fn(),
    importCommunity: vi.fn(),
    unpublish: vi.fn(),
    verify: vi.fn(),
    list: vi.fn(),
  },
  profilesApi: { create: vi.fn(), list: vi.fn() },
  ratingsApi: { get: vi.fn(), rate: vi.fn(), remove: vi.fn() },
  commentsApi: { list: vi.fn(), create: vi.fn(), remove: vi.fn() },
  moderationApi: { updateMeta: vi.fn() },
}));

vi.mock('../lib/setupApi', async () => {
  const actual = await vi.importActual<typeof import('../lib/setupApi')>('../lib/setupApi');
  return {
    ...actual,
    setupProfilesApi: { create: vi.fn(), update: vi.fn() },
    packUsageApi: { use: vi.fn() },
  };
});

vi.mock('../lib/packApi', () => ({
  packApi: {
    getPublicPack: vi.fn(),
    getPublicArtifacts: vi.fn(),
    listCommunity: vi.fn(),
  },
}));

const basePack: Collection = {
  id: 'pack-1',
  owner_id: 'other-user',
  name: 'Security & Compliance',
  description: 'Adversarial review and an audit trail.',
  git_url: '',
  git_branch: 'main',
  collection_type: 'additional',
  visibility: 'public',
  is_active: true,
  artifact_count: 2,
  download_count: 410,
  published: true,
  category: 'Governance & Security',
  is_starter_pack: false,
  avg_rating: 4.9,
  rating_count: 4,
  moderation_status: 'approved',
  created_at: '2026-01-01T00:00:00Z',
  updated_at: '2026-01-01T00:00:00Z',
};

const artifacts = [
  {
    id: 'art-1',
    collection_id: 'pack-1',
    artifact_type: 'rule',
    name: 'OWASP checklist',
    version: '1.0.0',
    priority: 80,
    target_compatibility: [],
    tags: [],
    description: 'Review every endpoint.',
    body: 'Check injection, authz, and secrets.',
    file_path: 'AGENTS.md',
    is_enabled: true,
    created_at: '2026-01-01T00:00:00Z',
    updated_at: '2026-01-01T00:00:00Z',
  },
  {
    id: 'art-2',
    collection_id: 'pack-1',
    artifact_type: 'skill',
    name: 'Audit trail',
    version: '1.0.0',
    priority: 50,
    target_compatibility: [],
    tags: [],
    description: null,
    body: 'Record what changed and why.',
    file_path: 'skills/audit/SKILL.md',
    is_enabled: true,
    created_at: '2026-01-01T00:00:00Z',
    updated_at: '2026-01-01T00:00:00Z',
  },
] as never;

function renderDetail() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={['/packs/pack-1']}>
        <Routes>
          <Route path="/packs/:id" element={<PackDetail />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe('PackDetail', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(collectionsApi.list).mockResolvedValue([]);
    vi.mocked(profilesApi.list).mockResolvedValue([]);
    vi.mocked(adaptersApi.list).mockResolvedValue([
      { name: 'claude-code', description: '', targets: [], enabled: true },
      { name: 'opencode', description: '', targets: [], enabled: true },
    ]);
    vi.mocked(setupProfilesApi.create).mockResolvedValue({
      ...basePack,
      id: 'setup-new',
    } as never);
    vi.mocked(setupProfilesApi.update).mockResolvedValue({
      ...basePack,
      id: 'setup-1',
    } as never);
    vi.mocked(packUsageApi.use).mockResolvedValue({});
    vi.mocked(packApi.listCommunity).mockResolvedValue({ items: [], total: 0 });
    vi.mocked(ratingsApi.get).mockResolvedValue({ avg_rating: 4.9, rating_count: 4, my_rating: null });
    vi.mocked(commentsApi.list).mockResolvedValue([]);
  });

  it('renders a public community pack anonymously with sign-up actions', async () => {
    mockUser = null;
    vi.mocked(packApi.getPublicPack).mockResolvedValue(basePack as never);
    vi.mocked(packApi.getPublicArtifacts).mockResolvedValue(artifacts);

    renderDetail();

    expect(await screen.findByRole('heading', { name: 'Security & Compliance' })).toBeInTheDocument();
    expect(screen.getAllByText('Add-on').length).toBeGreaterThan(0);
    expect(screen.getAllByText('Community').length).toBeGreaterThan(0);
    expect(screen.getAllByText('Governance & Security').length).toBeGreaterThan(0);

    const useLinks = screen.getAllByRole('link', { name: 'Use this pack' });
    expect(useLinks[0]).toHaveAttribute('href', '/login?mode=register');
    expect(screen.getByRole('link', { name: 'Sign up to build a setup' })).toHaveAttribute(
      'href',
      '/login?mode=register',
    );
    // No authenticated rating/comment requests for an anonymous visitor.
    expect(ratingsApi.get).not.toHaveBeenCalled();
    expect(commentsApi.list).not.toHaveBeenCalled();
  });

  it('switches to the contents tab and expands an item', async () => {
    mockUser = null;
    vi.mocked(packApi.getPublicPack).mockResolvedValue(basePack as never);
    vi.mocked(packApi.getPublicArtifacts).mockResolvedValue(artifacts);

    renderDetail();
    await screen.findByRole('heading', { name: 'Security & Compliance' });

    fireEvent.click(screen.getByRole('tab', { name: 'Contents' }));
    expect(await screen.findByText('OWASP checklist')).toBeInTheDocument();
    expect(screen.getByText('Audit trail')).toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: 'Expand OWASP checklist' }));
    expect(await screen.findByText('Check injection, authz, and secrets.')).toBeInTheDocument();
  });

  it('presents a pack permission policy as readable rules, not a model config', async () => {
    mockUser = null;
    const policy = {
      ...(artifacts as unknown as Record<string, unknown>[])[0],
      id: 'art-policy',
      artifact_type: 'model_config',
      name: 'permissions:default',
      description: 'Global permission rules (ask/deny only)',
      body: JSON.stringify({
        rules: [
          { capability: 'execute', effect: 'ask', match: 'git push *' },
          { capability: 'network', effect: 'deny', match: '' },
        ],
      }),
      file_path: 'permissions.json',
    };
    const reviewer = {
      ...(artifacts as unknown as Record<string, unknown>[])[0],
      id: 'art-agent',
      artifact_type: 'agent',
      name: 'code-reviewer',
      body: 'Review only.',
      permissions: { edit: 'deny', execute: 'ask', read: 'allow' },
    };
    vi.mocked(packApi.getPublicPack).mockResolvedValue(basePack as never);
    vi.mocked(packApi.getPublicArtifacts).mockResolvedValue([
      ...(artifacts as unknown as unknown[]),
      policy,
      reviewer,
    ] as never);

    renderDetail();
    await screen.findByRole('heading', { name: 'Security & Compliance' });
    fireEvent.click(screen.getByRole('tab', { name: 'Contents' }));

    // Its own filter, and it is not counted as (or listed under) a model config.
    expect(await screen.findByRole('button', { name: /^Permission rules \(1\)/ })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Model configs \(0\)/ })).toBeInTheDocument();
    expect(screen.queryByText('permissions:default')).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: 'Expand Permission rules' }));
    expect(await screen.findByText('git push *')).toBeInTheDocument();
    expect(screen.getByText('Run commands')).toBeInTheDocument();
    expect(screen.getByText('Ask first')).toBeInTheDocument();
    expect(screen.getByText('Blocked')).toBeInTheDocument();
    expect(screen.getByText(/never grant access/)).toBeInTheDocument();
    expect(screen.queryByText(/"capability"/)).not.toBeInTheDocument(); // no raw JSON

    // An agent's own restrictions read as sentences; `allow` shows nothing.
    fireEvent.click(screen.getByRole('button', { name: 'Expand code-reviewer' }));
    const list = await screen.findByRole('list', { name: 'Permission restrictions' });
    expect(list).toHaveTextContent('Cannot edit files');
    expect(list).toHaveTextContent('Asks before it can run commands');
    expect(list).not.toHaveTextContent('read');
  });

  it('shows the rating and comment surface to a signed-in non-owner', async () => {
    mockUser = { id: 'user-2', role: 'user' };
    vi.mocked(collectionsApi.get).mockResolvedValue(basePack as never);
    vi.mocked(collectionsApi.getArtifacts).mockResolvedValue(artifacts);
    vi.mocked(commentsApi.list).mockResolvedValue([
      {
        id: 'c-1',
        collection_id: 'pack-1',
        user_id: 'user-3',
        author_display_name: 'mira',
        body: 'The audit trail is the part that changed how I work.',
        created_at: '2026-01-01T00:00:00Z',
      },
    ]);

    renderDetail();
    await screen.findByRole('heading', { name: 'Security & Compliance' });

    fireEvent.click(screen.getByRole('tab', { name: 'Ratings & comments' }));
    expect(
      await screen.findByText('The audit trail is the part that changed how I work.'),
    ).toBeInTheDocument();
    expect(screen.getByPlaceholderText('Leave a comment...')).toBeInTheDocument();
    expect(ratingsApi.get).toHaveBeenCalledWith('pack-1');
    expect(screen.getByRole('button', { name: /Add to a setup/ })).toBeInTheDocument();
  });

  it('shows owner publish and manage actions plus the status tracker', async () => {
    mockUser = { id: 'owner-1', role: 'user' };
    vi.mocked(collectionsApi.get).mockResolvedValue({
      ...basePack,
      owner_id: 'owner-1',
      moderation_status: 'denied',
      moderation_reason: 'Please add a license.',
    } as never);
    vi.mocked(collectionsApi.getArtifacts).mockResolvedValue(artifacts);

    renderDetail();
    await screen.findByRole('heading', { name: 'Security & Compliance' });

    expect(screen.getByRole('link', { name: /Publish…/ })).toHaveAttribute(
      'href',
      '/packs/pack-1/publish',
    );
    expect(screen.getByRole('link', { name: /Manage items/ })).toHaveAttribute(
      'href',
      '/packs/pack-1/manage',
    );
    expect(screen.getByTestId('publish-status')).toBeInTheDocument();
    expect(screen.getByText(/Please add a license/)).toBeInTheDocument();
    expect(screen.queryByRole('link', { name: 'Use this pack' })).not.toBeInTheDocument();
  });

  it('creates a setup from a starting point and records the reference', async () => {
    mockUser = { id: 'user-2', role: 'user' };
    const starterPack = {
      ...basePack,
      id: 'pack-1',
      name: 'Software Engineer',
      collection_type: 'base',
      owner_id: 'starter',
      is_starter_pack: true,
    };
    vi.mocked(collectionsApi.get).mockResolvedValue(starterPack as never);
    vi.mocked(collectionsApi.getArtifacts).mockResolvedValue(artifacts);

    renderDetail();
    await screen.findByRole('heading', { name: 'Software Engineer' });

    const useButton = screen.getByRole('button', { name: 'Use this pack' });
    await waitFor(() => expect(useButton).toBeEnabled());
    fireEvent.click(useButton);

    await waitFor(() =>
      expect(setupProfilesApi.create).toHaveBeenCalledWith(
        expect.objectContaining({
          base_collection_id: 'pack-1',
          additional_collection_ids: [],
        }),
      ),
    );
    expect(packUsageApi.use).toHaveBeenCalledWith('pack-1');
  });

  it('pairs an add-on with a starting point and creates the setup with both', async () => {
    mockUser = { id: 'user-2', role: 'user' };
    const starterBase = {
      ...basePack,
      id: 'pack-base',
      name: 'Software Engineer',
      collection_type: 'base',
      download_count: 900,
      is_starter_pack: true,
    };
    vi.mocked(collectionsApi.get).mockResolvedValue(basePack as never);
    vi.mocked(collectionsApi.getArtifacts).mockResolvedValue(artifacts);
    vi.mocked(collectionsApi.list).mockResolvedValue([starterBase] as never);

    renderDetail();
    await screen.findByRole('heading', { name: 'Security & Compliance' });

    const useButton = screen.getByRole('button', { name: 'Use this pack' });
    await waitFor(() => expect(useButton).toBeEnabled());
    fireEvent.click(useButton);

    expect(await screen.findByRole('radio', { name: /Software Engineer/ })).toBeChecked();
    fireEvent.click(screen.getByRole('button', { name: /Create setup with this pack/ }));

    await waitFor(() =>
      expect(setupProfilesApi.create).toHaveBeenCalledWith(
        expect.objectContaining({
          base_collection_id: 'pack-base',
          additional_collection_ids: ['pack-1'],
        }),
      ),
    );
  });
});
