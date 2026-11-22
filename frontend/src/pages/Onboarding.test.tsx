import { render, screen, fireEvent, waitFor, cleanup } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter, Route, Routes, useLocation } from 'react-router-dom';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import Onboarding from './Onboarding';
import { adaptersApi, collectionsApi } from '../lib/api';
import {
  companionApi,
  fetchCompanionHealth,
  installsApi,
  onboardingApi,
  setupProfilesApi,
} from '../lib/setupApi';
import type { AdapterInfo, Artifact, Collection, Profile } from '../types';

vi.mock('../contexts/AuthContext', () => ({
  useAuth: () => ({ user: { id: 'user-1' }, refresh: vi.fn() }),
}));

vi.mock('../lib/api', () => ({
  adaptersApi: { list: vi.fn() },
  collectionsApi: { list: vi.fn(), getArtifacts: vi.fn() },
}));

vi.mock('../lib/setupApi', async () => {
  const actual = await vi.importActual<typeof import('../lib/setupApi')>('../lib/setupApi');
  return {
    ...actual,
    companionApi: { ...actual.companionApi, auditHome: vi.fn() },
    fetchCompanionHealth: vi.fn(),
    setupProfilesApi: { create: vi.fn(), update: vi.fn() },
    onboardingApi: { setCompleted: vi.fn() },
    installsApi: { list: vi.fn(), claim: vi.fn() },
  };
});

const adapter = (name: string): AdapterInfo => ({
  name,
  description: `${name} adapter`,
  targets: [name],
  enabled: true,
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
    artifact_count: 3,
    download_count: 10,
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

const collections: Collection[] = [
  pack({ id: 'pack-base', name: 'Software Engineer', download_count: 120 }),
  pack({ id: 'pack-devops', name: 'DevOps Engineer', download_count: 40 }),
  pack({ id: 'pack-data', name: 'Data Scientist', download_count: 20 }),
  pack({ id: 'pack-vibe', name: 'Vibecoder', download_count: 5 }),
  pack({
    id: 'pack-qa',
    name: 'QA / Test Engineer',
    collection_type: 'additional',
    download_count: 80,
  }),
  pack({
    id: 'pack-auditor',
    name: 'Auditor',
    collection_type: 'additional',
    download_count: 10,
  }),
];

const artifact = (id: string, name: string): Artifact => ({
  id,
  collection_id: 'pack-base',
  artifact_type: 'rule',
  name,
  version: '1.0.0',
  priority: 50,
  target_compatibility: [],
  tags: [],
  body: 'body',
  file_path: 'AGENTS.md',
  is_enabled: true,
  created_at: '2026-01-01T00:00:00Z',
  updated_at: '2026-01-01T00:00:00Z',
});

const createdProfile: Profile = {
  id: 'setup-1',
  owner_id: 'user-1',
  name: 'My setup',
  base_collection_id: 'pack-base',
  additional_collection_ids: [],
  disabled_artifact_ids: [],
  target_frameworks: ['claude-code'],
  is_public: false,
  version: 1,
  created_at: '2026-01-01T00:00:00Z',
  updated_at: '2026-01-01T00:00:00Z',
};

function LocationProbe() {
  const location = useLocation();
  return <div data-testid="path">{`${location.pathname}${location.search}`}</div>;
}

function renderWizard(path = '/onboarding') {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={[path]}>
        <Routes>
          <Route path="/onboarding" element={<Onboarding />} />
          <Route path="*" element={<LocationProbe />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

const continueButton = () => screen.getByRole('button', { name: /Continue|Finish/ });

async function selectFrameworkAndPack() {
  await screen.findByRole('heading', { name: 'What do you use?' });
  fireEvent.click(await screen.findByRole('button', { name: /Claude Code/ }));
  fireEvent.click(continueButton());
  await screen.findByRole('heading', { name: 'What should your agent know?' });
  fireEvent.click(await screen.findByRole('button', { name: /^Software Engineer/ }));
  fireEvent.click(continueButton());
  await screen.findByRole('heading', { name: 'Review your setup' });
}

async function reachInstallStep() {
  renderWizard();
  await selectFrameworkAndPack();
  fireEvent.click(continueButton());
  await screen.findByRole('heading', { name: 'Where should it go?' });
  fireEvent.click(continueButton());
  await screen.findByRole('heading', { name: 'Install your setup' });
}

describe('Onboarding wizard', () => {
  beforeEach(() => {
    cleanup();
    vi.clearAllMocks();
    window.localStorage.clear();
    vi.mocked(adaptersApi.list).mockResolvedValue([
      adapter('claude-code'),
      adapter('opencode'),
    ]);
    vi.mocked(collectionsApi.list).mockResolvedValue(collections);
    vi.mocked(collectionsApi.getArtifacts).mockResolvedValue([
      artifact('a1', 'Rule One'),
      artifact('a2', 'Rule Two'),
    ]);
    vi.mocked(fetchCompanionHealth).mockResolvedValue({
      status: 'ok',
      server: 'https://myace.example.com',
      apply: { supported: false, targets: [], machine_targets: [] },
      baseUrl: 'http://127.0.0.1:8765',
    });
    vi.mocked(companionApi.auditHome).mockResolvedValue({
      path: '/home',
      score: 60,
      targets: {},
    });
    vi.mocked(setupProfilesApi.create).mockResolvedValue(createdProfile);
    vi.mocked(setupProfilesApi.update).mockResolvedValue(createdProfile);
    vi.mocked(onboardingApi.setCompleted).mockResolvedValue({});
    vi.mocked(installsApi.claim).mockResolvedValue({
      id: 'claim-1',
      profile_id: 'setup-1',
      target: 'claude-code',
      location: 'machine',
      method: 'zip',
      created_at: '2026-01-01T00:00:00Z',
      updated_at: '2026-01-01T00:00:00Z',
    });
  });

  it('advances through the steps and creates the profile with target_frameworks', async () => {
    renderWizard();
    await selectFrameworkAndPack();

    expect(screen.getByText(/items total/i)).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText('Setup name'), {
      target: { value: 'My setup' },
    });
    fireEvent.click(continueButton());

    await screen.findByRole('heading', { name: 'Where should it go?' });
    fireEvent.click(continueButton());

    await screen.findByRole('heading', { name: 'Install your setup' });

    expect(setupProfilesApi.create).toHaveBeenCalledWith(
      expect.objectContaining({
        name: 'My setup',
        base_collection_id: 'pack-base',
        target_frameworks: ['claude-code'],
      }),
    );
    expect(setupProfilesApi.update).not.toHaveBeenCalled();
  });

  it('goes back to the previous step', async () => {
    renderWizard();
    await screen.findByRole('heading', { name: 'What do you use?' });
    fireEvent.click(await screen.findByRole('button', { name: /Claude Code/ }));
    fireEvent.click(continueButton());
    await screen.findByRole('heading', { name: 'What should your agent know?' });

    fireEvent.click(screen.getByRole('button', { name: 'Back' }));

    expect(
      await screen.findByRole('heading', { name: 'What do you use?' }),
    ).toBeInTheDocument();
  });

  it('Skip for now marks onboarding complete and returns Home', async () => {
    renderWizard();
    await screen.findByRole('heading', { name: 'What do you use?' });

    fireEvent.click(screen.getByRole('button', { name: /Skip for now/ }));

    await waitFor(() => expect(onboardingApi.setCompleted).toHaveBeenCalledWith(true));
    expect(await screen.findByTestId('path')).toHaveTextContent(/^\/$/);
    expect(setupProfilesApi.create).not.toHaveBeenCalled();
  });

  it('resumes at the step and pack named in the query string', async () => {
    renderWizard('/onboarding?step=3&pack=pack-base');

    expect(
      await screen.findByRole('heading', { name: 'Review your setup' }),
    ).toBeInTheDocument();
    expect(await screen.findByText('Software Engineer')).toBeInTheDocument();
  });

  it('resumes from a localStorage draft when the URL has no step', async () => {
    window.localStorage.setItem(
      'myace.onboarding.v1',
      JSON.stringify({
        step: 2,
        frameworks: ['claude-code'],
        basePackId: 'pack-base',
        addOnPackIds: [],
        name: 'Draft setup',
      }),
    );

    renderWizard();

    expect(
      await screen.findByRole('heading', { name: 'What should your agent know?' }),
    ).toBeInTheDocument();
  });

  it('asks which starting point to pair an add-on with, preselecting the most-used base', async () => {
    renderWizard();
    await screen.findByRole('heading', { name: 'What do you use?' });
    fireEvent.click(await screen.findByRole('button', { name: /Claude Code/ }));
    fireEvent.click(continueButton());
    await screen.findByRole('heading', { name: 'What should your agent know?' });

    fireEvent.click(screen.getByRole('button', { name: /^QA \/ Test Engineer/ }));

    expect(await screen.findByText(/Pair “QA \/ Test Engineer” with a starting point/)).toBeInTheDocument();
    // Software Engineer has the highest use count, so it is preselected.
    expect(screen.getByRole('radio', { name: /Software Engineer/ })).toBeChecked();
    expect(screen.getByRole('radio', { name: /DevOps Engineer/ })).not.toBeChecked();

    fireEvent.click(screen.getByRole('button', { name: /Use this starting point/ }));
    fireEvent.click(continueButton());

    expect(
      await screen.findByRole('heading', { name: 'Review your setup' }),
    ).toBeInTheDocument();
    expect(await screen.findByText('QA / Test Engineer')).toBeInTheDocument();
  });

  it('records an install claim and finishes on the setup page', async () => {
    globalThis.URL.createObjectURL = vi.fn(() => 'blob:mock-url');
    globalThis.URL.revokeObjectURL = vi.fn();
    vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(() => {});
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: true,
      blob: () => Promise.resolve(new Blob(['zip'], { type: 'application/zip' })),
    }) as unknown as typeof fetch;

    await reachInstallStep();

    fireEvent.click(screen.getByRole('button', { name: 'Download .zip' }));

    await waitFor(() =>
      expect(installsApi.claim).toHaveBeenCalledWith('setup-1', {
        target: 'claude-code',
        location: 'machine',
        method: 'zip',
      }),
    );
    expect(await screen.findByText('Installed, not verified')).toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: 'Finish' }));

    await waitFor(() => expect(onboardingApi.setCompleted).toHaveBeenCalledWith(true));
    expect(await screen.findByTestId('path')).toHaveTextContent('/setups/setup-1');
  });
});
