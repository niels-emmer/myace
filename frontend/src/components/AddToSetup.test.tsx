import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter, Route, Routes, useLocation } from 'react-router-dom';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import AddToSetup from './AddToSetup';
import { adaptersApi, collectionsApi, profilesApi } from '../lib/api';
import { packUsageApi, setupProfilesApi } from '../lib/setupApi';
import type { Collection, Profile } from '../types';

vi.mock('../contexts/AuthContext', () => ({
  useAuth: () => ({ user: { id: 'user-1' } }),
}));

vi.mock('../lib/api', () => ({
  adaptersApi: { list: vi.fn() },
  collectionsApi: { list: vi.fn() },
  profilesApi: { list: vi.fn() },
}));

vi.mock('../lib/setupApi', async () => {
  const actual = await vi.importActual<typeof import('../lib/setupApi')>('../lib/setupApi');
  return {
    ...actual,
    setupProfilesApi: { create: vi.fn(), update: vi.fn() },
    packUsageApi: { use: vi.fn() },
  };
});

function pack(overrides: Partial<Collection>): Collection {
  return {
    id: 'pack',
    owner_id: 'starter-owner',
    name: 'Pack',
    git_url: '',
    git_branch: 'main',
    collection_type: 'base',
    visibility: 'public',
    is_active: true,
    artifact_count: 10,
    download_count: 1,
    published: true,
    is_starter_pack: true,
    avg_rating: 4,
    rating_count: 1,
    moderation_status: 'approved',
    created_at: '2026-01-01T00:00:00Z',
    updated_at: '2026-01-01T00:00:00Z',
    ...overrides,
  };
}

const baseA = pack({ id: 'pack-base', name: 'Software Engineer', download_count: 100 });
const baseB = pack({ id: 'pack-devops', name: 'DevOps Engineer', download_count: 10 });
const addOn = pack({
  id: 'pack-qa',
  name: 'QA / Test Engineer',
  collection_type: 'additional',
  download_count: 50,
});

const setup: Profile = {
  id: 'setup-1',
  owner_id: 'user-1',
  name: 'My setup',
  base_collection_id: 'pack-base',
  additional_collection_ids: ['pack-auditor'],
  disabled_artifact_ids: [],
  target_frameworks: ['claude-code'],
  is_public: false,
  version: 1,
  created_at: '2026-01-01T00:00:00Z',
  updated_at: '2026-01-01T00:00:00Z',
};

const created: Profile = {
  ...setup,
  id: 'setup-new',
  name: 'QA / Test Engineer setup',
  additional_collection_ids: [],
};

function LocationProbe() {
  const location = useLocation();
  return <div data-testid="path">{location.pathname}</div>;
}

function renderFor(collection: Collection, frameworks?: string[]) {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={['/packs/pack-qa']}>
        <Routes>
          <Route
            path="/packs/:id"
            element={<AddToSetup collection={collection} frameworks={frameworks} />}
          />
          <Route path="*" element={<LocationProbe />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe('AddToSetup', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(collectionsApi.list).mockResolvedValue([baseA, baseB, addOn]);
    vi.mocked(adaptersApi.list).mockResolvedValue([
      { name: 'claude-code', description: '', targets: [], enabled: true },
      { name: 'opencode', description: '', targets: [], enabled: true },
    ]);
    vi.mocked(profilesApi.list).mockResolvedValue([setup]);
    vi.mocked(setupProfilesApi.create).mockResolvedValue(created);
    vi.mocked(setupProfilesApi.update).mockResolvedValue(setup);
    vi.mocked(packUsageApi.use).mockResolvedValue({});
  });

  it('pairs an add-on with the most-used starting point before creating a setup', async () => {
    renderFor(addOn);

    const useButton = screen.getByRole('button', { name: 'Use this pack' });
    await waitFor(() => expect(useButton).toBeEnabled());
    fireEvent.click(useButton);

    expect(await screen.findByRole('radio', { name: /Software Engineer/ })).toBeChecked();
    fireEvent.click(screen.getByRole('button', { name: /Create setup with this pack/ }));

    await waitFor(() =>
      expect(setupProfilesApi.create).toHaveBeenCalledWith(
        expect.objectContaining({
          base_collection_id: 'pack-base',
          additional_collection_ids: ['pack-qa'],
        }),
      ),
    );
    expect(packUsageApi.use).toHaveBeenCalledWith('pack-qa');
    expect(await screen.findByTestId('path')).toHaveTextContent('/setups/setup-new');
  });

  it('creates a setup directly from a starting-point pack', async () => {
    renderFor(baseA);

    const useButton = screen.getByRole('button', { name: 'Use this pack' });
    await waitFor(() => expect(useButton).toBeEnabled());
    fireEvent.click(useButton);

    await waitFor(() =>
      expect(setupProfilesApi.create).toHaveBeenCalledWith(
        expect.objectContaining({
          base_collection_id: 'pack-base',
          additional_collection_ids: [],
        }),
      ),
    );
  });

  it('appends an add-on to an existing setup instead of only bumping a counter', async () => {
    renderFor(addOn);

    fireEvent.click(screen.getByRole('button', { name: /Add to a setup/ }));
    fireEvent.click(await screen.findByRole('button', { name: /My setup/ }));

    await waitFor(() =>
      expect(setupProfilesApi.update).toHaveBeenCalledWith(
        'setup-1',
        expect.objectContaining({
          base_collection_id: 'pack-base',
          additional_collection_ids: ['pack-auditor', 'pack-qa'],
        }),
      ),
    );
    expect(await screen.findByTestId('path')).toHaveTextContent('/setups/setup-1');
  });

  it('forwards frameworks the pack declares into the new setup', async () => {
    renderFor(baseA, ['claude-code', 'opencode']);

    const useButton = screen.getByRole('button', { name: 'Use this pack' });
    await waitFor(() => expect(useButton).toBeEnabled());
    fireEvent.click(useButton);

    await waitFor(() =>
      expect(setupProfilesApi.create).toHaveBeenCalledWith(
        expect.objectContaining({
          target_frameworks: ['claude-code', 'opencode'],
        }),
      ),
    );
  });

  it('caps a generated setup name at the profile column limit', async () => {
    const longBase = pack({
      id: 'pack-long',
      name: 'X'.repeat(300),
      download_count: 5,
    });
    renderFor(longBase);

    const useButton = screen.getByRole('button', { name: 'Use this pack' });
    await waitFor(() => expect(useButton).toBeEnabled());
    fireEvent.click(useButton);

    await waitFor(() => expect(setupProfilesApi.create).toHaveBeenCalled());
    const payload = vi.mocked(setupProfilesApi.create).mock.calls[0][0];
    expect(payload.name).toHaveLength(255);
    expect(payload.name.endsWith(' setup')).toBe(true);
  });

  it('refuses to add a pack that is already the setup’s base', async () => {
    vi.mocked(profilesApi.list).mockResolvedValue([
      { ...setup, base_collection_id: 'pack-qa', additional_collection_ids: [] },
    ]);
    renderFor(addOn);

    fireEvent.click(screen.getByRole('button', { name: /Add to a setup/ }));
    fireEvent.click(await screen.findByRole('button', { name: /My setup/ }));

    expect(
      await screen.findByText(/already this setup’s starting point/i),
    ).toBeInTheDocument();
    expect(setupProfilesApi.update).not.toHaveBeenCalled();

    // Re-opening the menu must not leave the row disabled (no stuck busy state).
    fireEvent.click(screen.getByRole('button', { name: /Add to a setup/ }));
    expect(await screen.findByRole('button', { name: /My setup/ })).toBeEnabled();
  });

  it('uses a starting-point pack as the base when attaching to an existing setup', async () => {
    renderFor(baseB);

    fireEvent.click(screen.getByRole('button', { name: /Add to a setup/ }));
    fireEvent.click(await screen.findByRole('button', { name: /My setup/ }));

    await waitFor(() =>
      expect(setupProfilesApi.update).toHaveBeenCalledWith(
        'setup-1',
        expect.objectContaining({
          base_collection_id: 'pack-devops',
          additional_collection_ids: ['pack-auditor'],
          target_frameworks: ['claude-code'],
        }),
      ),
    );
  });
});
