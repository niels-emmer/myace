import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter } from 'react-router-dom';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import ProfileComposer from './ProfileComposer';
import { profilesApi, collectionsApi, adaptersApi } from '../lib/api';
import type { Collection, Artifact, AdapterInfo } from '../types';

vi.mock('../lib/api', () => ({
  profilesApi: { list: vi.fn(), create: vi.fn() },
  collectionsApi: { list: vi.fn(), getArtifacts: vi.fn() },
  adaptersApi: { list: vi.fn() },
}));

const baseCollection: Collection = {
  id: 'base-1',
  owner_id: 'owner-1',
  name: 'Software Engineer',
  git_url: '',
  git_branch: 'main',
  collection_type: 'base',
  visibility: 'private',
  is_active: true,
  artifact_count: 1,
  download_count: 0,
  published: false,
  avg_rating: 0,
  rating_count: 0,
  moderation_status: 'draft',
  created_at: '2026-01-01T00:00:00Z',
  updated_at: '2026-01-01T00:00:00Z',
};

const additionalCollection: Collection = {
  ...baseCollection,
  id: 'add-1',
  name: 'My Community Pack',
  collection_type: 'additional',
};

const builderInBase: Artifact = {
  id: 'art-base-builder',
  collection_id: 'base-1',
  artifact_type: 'agent',
  name: 'builder',
  version: '1.0.0',
  priority: 50,
  target_compatibility: [],
  tags: [],
  body: '',
  file_path: 'agents/builder.md',
  is_enabled: true,
  created_at: '2026-01-01T00:00:00Z',
  updated_at: '2026-01-01T00:00:00Z',
};

const builderInAdditional: Artifact = {
  ...builderInBase,
  id: 'art-add-builder',
  collection_id: 'add-1',
};

const adapter: AdapterInfo = {
  name: 'opencode',
  description: 'OpenCode adapter',
  targets: ['opencode'],
  enabled: true,
};

function renderWithQueryClient() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>
        <ProfileComposer />
      </MemoryRouter>
    </QueryClientProvider>
  );
}

async function openForm() {
  fireEvent.click(await screen.findByRole('button', { name: /Add profile/i }));
}

describe('ProfileComposer pre-compile collision preview', () => {
  beforeEach(() => {
    vi.mocked(profilesApi.list).mockResolvedValue([]);
    vi.mocked(profilesApi.create).mockResolvedValue({} as never);
    vi.mocked(collectionsApi.list).mockResolvedValue([baseCollection, additionalCollection]);
    vi.mocked(adaptersApi.list).mockResolvedValue([adapter]);
  });

  it('shows a collision panel naming both collections and the winner when a base + additional share an artifact name', async () => {
    vi.mocked(collectionsApi.getArtifacts).mockImplementation((cid: string) => {
      if (cid === 'base-1') return Promise.resolve([builderInBase]);
      if (cid === 'add-1') return Promise.resolve([builderInAdditional]);
      return Promise.resolve([]);
    });

    renderWithQueryClient();
    await openForm();

    // Select the base collection.
    fireEvent.click(await screen.findByRole('button', { name: /Software Engineer/i }));
    // Select the additional collection.
    fireEvent.click(screen.getByRole('button', { name: /My Community Pack/i }));

    expect(await screen.findByText(/1 name collision across these collections/i)).toBeInTheDocument();
    // The collision message names both collections and the winner.
    expect(screen.getByText(/is defined in both Software Engineer and My Community Pack/)).toBeInTheDocument();
    expect(screen.getByText(/My Community Pack wins/)).toBeInTheDocument();
  });

  it('clicking "Disable in this profile" adds the losing artifact id and clears the collision', async () => {
    vi.mocked(collectionsApi.getArtifacts).mockImplementation((cid: string) => {
      if (cid === 'base-1') return Promise.resolve([builderInBase]);
      if (cid === 'add-1') return Promise.resolve([builderInAdditional]);
      return Promise.resolve([]);
    });

    renderWithQueryClient();
    await openForm();

    fireEvent.click(await screen.findByRole('button', { name: /Software Engineer/i }));
    fireEvent.click(screen.getByRole('button', { name: /My Community Pack/i }));

    expect(await screen.findByText(/1 name collision across these collections/i)).toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: /Disable in this profile/i }));

    // The collision disappears immediately.
    await waitFor(() =>
      expect(screen.queryByText(/1 name collision across these collections/i)).not.toBeInTheDocument()
    );

    // Fill the required Profile Name so the form can submit (jsdom enforces
    // constraint validation on submit). The label isn't associated via
    // htmlFor, so target the first textbox (the name input).
    fireEvent.change(screen.getAllByRole('textbox')[0], { target: { value: 'My Profile' } });

    // Saving the profile sends the losing artifact id in disabled_artifact_ids.
    fireEvent.click(screen.getByRole('button', { name: /Save Profile/i }));
    await waitFor(() => expect(profilesApi.create).toHaveBeenCalled());
    expect(profilesApi.create).toHaveBeenCalledWith(
      expect.objectContaining({ disabled_artifact_ids: ['art-base-builder'] })
    );
  });

  it('renders no panel for a collision-free selection', async () => {
    // Only the base collection has a 'builder'; the additional has a distinct name.
    const reviewerInAdditional: Artifact = {
      ...builderInAdditional,
      id: 'art-add-reviewer',
      name: 'reviewer',
    };
    vi.mocked(collectionsApi.getArtifacts).mockImplementation((cid: string) => {
      if (cid === 'base-1') return Promise.resolve([builderInBase]);
      if (cid === 'add-1') return Promise.resolve([reviewerInAdditional]);
      return Promise.resolve([]);
    });

    renderWithQueryClient();
    await openForm();

    fireEvent.click(await screen.findByRole('button', { name: /Software Engineer/i }));
    fireEvent.click(screen.getByRole('button', { name: /My Community Pack/i }));

    await waitFor(() => expect(collectionsApi.getArtifacts).toHaveBeenCalledWith('base-1'));
    expect(screen.queryByText(/name collision/i)).not.toBeInTheDocument();
  });
});
