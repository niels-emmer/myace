import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import PublishPack from './PublishPack';
import { collectionsApi } from '../lib/api';
import { packApi } from '../lib/packApi';
import type { Collection } from '../types';

vi.mock('../contexts/AuthContext', () => ({
  useAuth: () => ({ user: { id: 'owner-1', role: 'user' }, isLoading: false }),
}));

vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom');
  return {
    ...actual,
    useNavigate: () => vi.fn(),
  };
});

vi.mock('../lib/api', () => ({
  collectionsApi: {
    get: vi.fn(),
    list: vi.fn(),
    listCommunityCategories: vi.fn(),
    publish: vi.fn(),
    unpublish: vi.fn(),
  },
}));

vi.mock('../lib/packApi', () => ({
  packApi: { updateMetadata: vi.fn() },
}));

const pack: Collection = {
  id: 'pack-1',
  owner_id: 'owner-1',
  name: 'My backend rules',
  description: 'Transaction boundaries, error contracts, and migrations.',
  git_url: '',
  git_branch: 'main',
  collection_type: 'additional',
  visibility: 'private',
  is_active: true,
  artifact_count: 14,
  download_count: 0,
  published: false,
  category: 'Backend',
  is_starter_pack: false,
  avg_rating: 0,
  rating_count: 0,
  moderation_status: 'draft',
  created_at: '2026-01-01T00:00:00Z',
  updated_at: '2026-01-01T00:00:00Z',
};

function renderWizard() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={['/packs/pack-1/publish']}>
        <Routes>
          <Route path="/packs/:id/publish" element={<PublishPack />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe('PublishPack', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(collectionsApi.get).mockResolvedValue(pack);
    vi.mocked(collectionsApi.list).mockResolvedValue([pack]);
    vi.mocked(collectionsApi.listCommunityCategories).mockResolvedValue(['Backend', 'Frontend']);
    vi.mocked(packApi.updateMetadata).mockResolvedValue(pack as never);
    vi.mocked(collectionsApi.publish).mockResolvedValue({
      ...pack,
      moderation_status: 'submitted',
    });
  });

  it('walks all four steps and submits metadata + the review request', async () => {
    renderWizard();

    expect(await screen.findByRole('heading', { name: 'Publish a pack' })).toBeInTheDocument();
    expect(screen.getByText('My backend rules')).toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: 'Continue' }));
    const license = await screen.findByLabelText(/License/);
    fireEvent.change(license, { target: { value: 'MIT' } });

    fireEvent.click(screen.getByRole('button', { name: 'Continue' }));
    expect(await screen.findByText('This is what people will see before using the pack.')).toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: 'Continue' }));
    fireEvent.click(screen.getByRole('button', { name: /Submit for review/i }));

    await waitFor(() => expect(packApi.updateMetadata).toHaveBeenCalledTimes(1));
    expect(packApi.updateMetadata).toHaveBeenCalledWith('pack-1', {
      name: 'My backend rules',
      description: 'Transaction boundaries, error contracts, and migrations.',
      category: 'Backend',
      license: 'MIT',
    });
    expect(collectionsApi.publish).toHaveBeenCalledWith('pack-1', {
      category: 'Backend',
      publish_name: 'My backend rules',
      publish_description: 'Transaction boundaries, error contracts, and migrations.',
    });
    expect(await screen.findByText(/Submitted\. You are in the moderation queue\./)).toBeInTheDocument();
  });

  it('shows the moderator reason when changes were requested', async () => {
    vi.mocked(collectionsApi.get).mockResolvedValue({
      ...pack,
      moderation_status: 'denied',
      moderation_reason: 'Please add a license.',
    });

    renderWizard();
    expect((await screen.findAllByText(/Changes requested/)).length).toBeGreaterThan(0);
    expect(screen.getByText(/Please add a license\./)).toBeInTheDocument();
  });

  it('does not let a non-owner publish', async () => {
    vi.mocked(collectionsApi.get).mockResolvedValue({ ...pack, owner_id: 'someone-else' });

    renderWizard();
    expect(
      await screen.findByText(/Only the pack's owner can publish it/i),
    ).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /Submit for review/i })).not.toBeInTheDocument();
  });
});
