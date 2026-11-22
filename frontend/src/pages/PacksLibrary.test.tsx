import { render, screen, fireEvent, within } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter } from 'react-router-dom';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import PacksLibrary from './PacksLibrary';
import { collectionsApi } from '../lib/api';
import type { Collection } from '../types';

vi.mock('../contexts/AuthContext', () => ({
  useAuth: () => ({ user: { id: 'user-1' } }),
}));

vi.mock('../lib/api', () => ({
  collectionsApi: { list: vi.fn(), listCommunityCategories: vi.fn() },
}));

const minePack: Collection = {
  id: 'mine-pack',
  owner_id: 'user-1',
  name: 'My House Rules',
  description: 'Personal conventions for my projects.',
  git_url: '',
  git_branch: 'main',
  collection_type: 'base',
  visibility: 'private',
  is_active: true,
  artifact_count: 5,
  download_count: 3,
  published: false,
  is_starter_pack: false,
  avg_rating: 0,
  rating_count: 0,
  moderation_status: 'draft',
  created_at: '2026-01-01T00:00:00Z',
  updated_at: '2026-01-01T00:00:00Z',
};

const starterPack: Collection = {
  ...minePack,
  id: 'starter-pack',
  owner_id: 'starter-owner',
  name: 'Software Engineer',
  description: 'A complete starting point for production code.',
  collection_type: 'base',
  visibility: 'public',
  published: true,
  is_starter_pack: true,
  category: 'Base Profiles',
  avg_rating: 4.8,
  rating_count: 12,
  download_count: 1200,
};

const communityAddon: Collection = {
  ...minePack,
  id: 'community-addon',
  owner_id: 'other-user',
  name: 'Security & Compliance',
  description: 'Adversarial review, OWASP checks and an audit trail.',
  collection_type: 'additional',
  visibility: 'public',
  published: true,
  is_starter_pack: false,
  category: 'Governance & Security',
  avg_rating: 4.9,
  rating_count: 4,
  download_count: 410,
};

const communityBase: Collection = {
  ...minePack,
  id: 'community-base',
  owner_id: 'other-user',
  name: 'ML Research Assistant',
  description: 'Reproducibility and eval-first experimentation.',
  visibility: 'public',
  published: true,
  category: 'AI/LLM Engineering',
  avg_rating: 4.6,
  rating_count: 2,
  download_count: 120,
};

function renderLibrary() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>
        <PacksLibrary />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

/** The result grid — excludes the always-present "Start here" bundle strip. */
async function results() {
  return within(await screen.findByTestId('packs-grid'));
}

describe('PacksLibrary', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(collectionsApi.list).mockResolvedValue([
      minePack,
      starterPack,
      communityAddon,
      communityBase,
    ]);
    vi.mocked(collectionsApi.listCommunityCategories).mockResolvedValue([
      'Base Profiles',
      'Governance & Security',
      'AI/LLM Engineering',
    ]);
  });

  it('shows every visible pack with kind and source badges', async () => {
    renderLibrary();
    const grid = await results();

    expect(grid.getByText('My House Rules')).toBeInTheDocument();
    expect(grid.getByText('Software Engineer')).toBeInTheDocument();
    expect(grid.getByText('Security & Compliance')).toBeInTheDocument();
    expect(grid.getByText('ML Research Assistant')).toBeInTheDocument();

    expect(grid.getByText('Mine')).toBeInTheDocument();
    expect(grid.getByText('Starter')).toBeInTheDocument();
    expect(grid.getAllByText('Community')).toHaveLength(2);
    expect(grid.getAllByText('Starting point')).toHaveLength(3);
    expect(grid.getByText('Add-on')).toBeInTheDocument();
  });

  it('filters to the packs the user owns', async () => {
    renderLibrary();
    await results();

    fireEvent.click(screen.getByRole('button', { name: 'Mine' }));
    const grid = await results();

    expect(grid.getByText('My House Rules')).toBeInTheDocument();
    expect(grid.queryByText('Software Engineer')).not.toBeInTheDocument();
    expect(grid.queryByText('Security & Compliance')).not.toBeInTheDocument();
  });

  it('filters by starting points and add-ons', async () => {
    renderLibrary();
    await results();

    fireEvent.click(screen.getByRole('button', { name: 'Starting points' }));
    let grid = await results();
    expect(grid.getByText('My House Rules')).toBeInTheDocument();
    expect(grid.getByText('Software Engineer')).toBeInTheDocument();
    expect(grid.getByText('ML Research Assistant')).toBeInTheDocument();
    expect(grid.queryByText('Security & Compliance')).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: 'Add-ons' }));
    grid = await results();
    expect(grid.queryByText('Software Engineer')).not.toBeInTheDocument();
    expect(grid.getByText('Security & Compliance')).toBeInTheDocument();
  });

  it('filters to community packs and links them to the community detail route', async () => {
    renderLibrary();
    await results();

    fireEvent.click(screen.getByRole('button', { name: 'Community' }));
    const grid = await results();

    expect(grid.queryByText('My House Rules')).not.toBeInTheDocument();
    expect(grid.queryByText('Software Engineer')).not.toBeInTheDocument();
    expect(grid.getByRole('link', { name: /Security & Compliance/ })).toHaveAttribute(
      'href',
      '/packs/community/community-addon',
    );
    expect(grid.getByRole('link', { name: /ML Research Assistant/ })).toHaveAttribute(
      'href',
      '/packs/community/community-base',
    );
  });

  it('searches name and description', async () => {
    renderLibrary();
    await results();

    fireEvent.change(screen.getByRole('searchbox', { name: /Search packs/i }), {
      target: { value: 'owasp' },
    });
    const grid = await results();

    expect(grid.getByText('Security & Compliance')).toBeInTheDocument();
    expect(grid.queryByText('My House Rules')).not.toBeInTheDocument();
    expect(grid.queryByText('Software Engineer')).not.toBeInTheDocument();
  });

  it('shows a create/import empty state when no pack matches', async () => {
    renderLibrary();
    await results();

    fireEvent.change(screen.getByRole('searchbox', { name: /Search packs/i }), {
      target: { value: 'zzzz-no-match' },
    });

    expect(await screen.findByText('No packs match these filters.')).toBeInTheDocument();
    expect(screen.getByRole('link', { name: /Create a pack/i })).toHaveAttribute('href', '/packs/mine');
    expect(screen.getAllByRole('link', { name: /Import packs/i }).length).toBeGreaterThan(0);
  });

  it('links owned and starter packs to the pack detail route', async () => {
    renderLibrary();
    const grid = await results();

    expect(grid.getByRole('link', { name: /My House Rules/ })).toHaveAttribute(
      'href',
      '/packs/mine-pack',
    );
    expect(grid.getByRole('link', { name: /Software Engineer/ })).toHaveAttribute(
      'href',
      '/packs/starter-pack',
    );

    // The "Start here" bundle strip links to the actual starter pack, not
    // the generic My packs landing page. Scope to the strip: the grid card
    // above would otherwise satisfy this assertion even if the strip regressed.
    const strip = within(screen.getByTestId('start-here'));
    expect(strip.getByRole('link', { name: /Software Engineer/ })).toHaveAttribute(
      'href',
      '/packs/starter-pack',
    );
  });
});
