import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import PackDetail from './PackDetail';
import { collectionsApi, commentsApi, profilesApi, ratingsApi } from '../lib/api';
import { packApi } from '../lib/packApi';
import type { Collection } from '../types';

let mockUser: { id: string; role: 'user' | 'moderator' | 'admin' } | null = null;

vi.mock('../contexts/AuthContext', () => ({
  useAuth: () => ({ user: mockUser, isLoading: false }),
}));

vi.mock('../lib/api', () => ({
  collectionsApi: {
    get: vi.fn(),
    getArtifacts: vi.fn(),
    importCommunity: vi.fn(),
    unpublish: vi.fn(),
    verify: vi.fn(),
  },
  profilesApi: { create: vi.fn() },
  ratingsApi: { get: vi.fn(), rate: vi.fn(), remove: vi.fn() },
  commentsApi: { list: vi.fn(), create: vi.fn(), remove: vi.fn() },
  moderationApi: { updateMeta: vi.fn() },
}));

vi.mock('../lib/packApi', () => ({
  packApi: {
    getPublicPack: vi.fn(),
    getPublicArtifacts: vi.fn(),
    listCommunity: vi.fn(),
    usePack: vi.fn(),
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

  it('creates a setup directly when a starting-point pack is used', async () => {
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
    vi.mocked(packApi.usePack).mockResolvedValue({
      collection_id: 'pack-1',
      download_count: 121,
    });
    vi.mocked(profilesApi.create).mockResolvedValue({ id: 'setup-2' } as never);

    renderDetail();
    await screen.findByRole('heading', { name: 'Software Engineer' });

    fireEvent.click(screen.getByRole('button', { name: 'Use this pack' }));

    await waitFor(() => expect(packApi.usePack).toHaveBeenCalledWith('pack-1'));
    expect(profilesApi.create).toHaveBeenCalledWith({
      name: 'Software Engineer',
      description: starterPack.description,
      base_collection_id: 'pack-1',
      additional_collection_ids: [],
    });
  });

  it('asks an add-on which starting point to pair with and records the use', async () => {
    mockUser = { id: 'user-2', role: 'user' };
    vi.mocked(collectionsApi.get).mockResolvedValue(basePack as never);
    vi.mocked(collectionsApi.getArtifacts).mockResolvedValue(artifacts);
    vi.mocked(packApi.listCommunity).mockResolvedValue({
      items: [
        {
          ...basePack,
          id: 'base-1',
          name: 'Software Engineer',
          collection_type: 'base',
          is_starter_pack: true,
          owner_id: 'starter',
        },
      ],
      total: 1,
    });
    vi.mocked(packApi.usePack).mockResolvedValue({
      collection_id: 'pack-1',
      download_count: 411,
    });
    vi.mocked(profilesApi.create).mockResolvedValue({
      id: 'setup-1',
      name: 'Software Engineer + Security & Compliance',
    } as never);

    renderDetail();
    await screen.findByRole('heading', { name: 'Security & Compliance' });

    fireEvent.click(screen.getByRole('button', { name: 'Use this pack' }));
    expect(
      await screen.findByRole('heading', { name: /Pair this add-on with a starting point/i }),
    ).toBeInTheDocument();
    await screen.findByRole('option', { name: 'Software Engineer' });

    const confirm = screen.getByRole('button', {
      name: 'Create setup with this add-on',
    });
    await waitFor(() => expect(confirm).toBeEnabled());
    fireEvent.click(confirm);
    await waitFor(() => expect(packApi.usePack).toHaveBeenCalledWith('pack-1'));
    // The chosen starting point is persisted as the new setup's base, and
    // the add-on as its additional pack — the pairing is not discarded.
    expect(profilesApi.create).toHaveBeenCalledWith(
      expect.objectContaining({
        base_collection_id: 'base-1',
        additional_collection_ids: ['pack-1'],
      }),
    );
  });
});
