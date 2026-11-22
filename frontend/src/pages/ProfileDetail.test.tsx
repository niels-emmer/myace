import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter } from 'react-router-dom';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import ProfileDetail from './ProfileDetail';
import { adaptersApi, collectionsApi, profilesApi, syncApi } from '../lib/api';
import { installsApi, setupProfilesApi } from '../lib/setupApi';
import type { Collection, CompileResult, Profile, SyncStatus } from '../types';

vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom');
  return {
    ...actual,
    useParams: () => ({ id: 'setup-1' }),
    useNavigate: () => vi.fn(),
  };
});

vi.mock('../contexts/AuthContext', () => ({
  useAuth: () => ({ user: { id: 'user-1', is_admin: false } }),
}));

vi.mock('../lib/api', () => ({
  collectionsApi: { list: vi.fn(), getArtifacts: vi.fn() },
  profilesApi: { get: vi.fn(), compile: vi.fn(), delete: vi.fn() },
  adaptersApi: { list: vi.fn() },
  syncApi: { getStatus: vi.fn() },
}));

vi.mock('../lib/setupApi', async () => {
  const actual = await vi.importActual<typeof import('../lib/setupApi')>('../lib/setupApi');
  return {
    ...actual,
    installsApi: { list: vi.fn() },
    setupProfilesApi: { update: vi.fn() },
  };
});

const basePack: Collection = {
  id: 'pack-base',
  owner_id: 'starter-owner',
  name: 'Software Engineer',
  git_url: '',
  git_branch: 'main',
  collection_type: 'base',
  visibility: 'public',
  is_active: true,
  artifact_count: 3,
  download_count: 40,
  published: true,
  is_starter_pack: true,
  avg_rating: 4.5,
  rating_count: 2,
  moderation_status: 'approved',
  created_at: '2026-01-01T00:00:00Z',
  updated_at: '2026-01-01T00:00:00Z',
};

const addOnPack: Collection = {
  ...basePack,
  id: 'pack-qa',
  name: 'QA / Test Engineer',
  collection_type: 'additional',
};

const profile: Profile = {
  id: 'setup-1',
  owner_id: 'user-1',
  name: 'My software setup',
  description: 'For my repo',
  base_collection_id: 'pack-base',
  additional_collection_ids: ['pack-qa'],
  disabled_artifact_ids: [],
  target_frameworks: ['claude-code', 'codex-cli', 'opencode', 'cursor'],
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
  last_checked_at: '2026-02-01T00:00:00Z',
  ...overrides,
});

const compileResult = (warnings: CompileResult['warnings']): CompileResult => ({
  profile_id: 'setup-1',
  profile_name: 'My software setup',
  target: 'claude-code',
  artifact_count: 3,
  files: { 'CLAUDE.md': '# Agents' },
  warnings,
  compiled_hash: 'hash',
});

function renderSetup() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>
        <ProfileDetail />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe('ProfileDetail framework matrix', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(profilesApi.get).mockResolvedValue(profile);
    vi.mocked(profilesApi.compile).mockResolvedValue(compileResult([]));
    vi.mocked(collectionsApi.list).mockResolvedValue([basePack, addOnPack]);
    vi.mocked(collectionsApi.getArtifacts).mockResolvedValue([
      {
        id: 'a1',
        collection_id: 'pack-base',
        artifact_type: 'rule',
        name: 'Rule One',
        version: '1.0.0',
        priority: 50,
        target_compatibility: [],
        tags: [],
        body: 'body',
        file_path: 'AGENTS.md',
        is_enabled: true,
        created_at: '2026-01-01T00:00:00Z',
        updated_at: '2026-01-01T00:00:00Z',
      },
    ]);
    vi.mocked(adaptersApi.list).mockResolvedValue([]);
    vi.mocked(syncApi.getStatus).mockResolvedValue([]);
    vi.mocked(installsApi.list).mockResolvedValue([]);
    vi.mocked(setupProfilesApi.update).mockResolvedValue(profile);
  });

  it('applies verified > drift > installed-not-verified > not-installed precedence', async () => {
    vi.mocked(syncApi.getStatus).mockResolvedValue([
      syncRow(),
      syncRow({ id: 'sync-2', target: 'codex-cli', in_sync: false }),
    ]);
    vi.mocked(installsApi.list).mockResolvedValue([
      {
        id: 'claim-1',
        profile_id: 'setup-1',
        target: 'opencode',
        location: 'machine',
        method: 'zip',
        created_at: '2026-01-01T00:00:00Z',
        updated_at: '2026-01-01T00:00:00Z',
      },
    ]);

    renderSetup();

    expect(await screen.findByText('Verified in sync')).toBeInTheDocument();
    expect(screen.getByText('Changes since install')).toBeInTheDocument();
    expect(screen.getByText('Installed, not verified')).toBeInTheDocument();
    expect(screen.getByText('Not installed')).toBeInTheDocument();
    // Location comes from the install claim, not invented for sync-only rows.
    expect(screen.getByText('~/.config/opencode')).toBeInTheDocument();
  });

  it('persists a preferred target without dropping the other frameworks', async () => {
    vi.mocked(adaptersApi.list).mockResolvedValue([
      { name: 'opencode', description: 'OpenCode', targets: ['opencode'], enabled: true },
    ]);
    renderSetup();
    await screen.findByText('My software setup');

    fireEvent.click(screen.getByRole('button', { name: /^Edit$/ }));
    const selects = screen.getAllByRole('combobox');
    fireEvent.change(selects[selects.length - 1], { target: { value: 'opencode' } });
    fireEvent.click(screen.getByRole('button', { name: /^Save$/ }));

    await waitFor(() =>
      expect(setupProfilesApi.update).toHaveBeenCalledWith(
        'setup-1',
        expect.objectContaining({
          target_framework: 'opencode',
          target_frameworks: ['claude-code', 'codex-cli', 'opencode', 'cursor'],
        }),
      ),
    );
  });

  it('adds a framework from the advanced section', async () => {
    vi.mocked(adaptersApi.list).mockResolvedValue([
      { name: 'claude-code', description: '', targets: [], enabled: true },
      { name: 'windsurf', description: '', targets: [], enabled: true },
    ]);
    renderSetup();
    await screen.findByText('My software setup');

    fireEvent.click(screen.getByText(/Advanced — item toggles/i));
    fireEvent.click(screen.getByRole('button', { name: 'Windsurf' }));

    await waitFor(() =>
      expect(setupProfilesApi.update).toHaveBeenCalledWith(
        'setup-1',
        expect.objectContaining({
          target_frameworks: ['claude-code', 'codex-cli', 'opencode', 'cursor', 'windsurf'],
        }),
      ),
    );
  });

  it('renders compile warnings as advisory amber copy', async () => {
    vi.mocked(profilesApi.compile).mockResolvedValue(
      compileResult([
        {
          level: 'warning',
          code: 'name_collision',
          message: "Artifact 'test-patterns' is defined in both packs; QA wins.",
        },
      ]),
    );

    renderSetup();

    expect(await screen.findByText(/test-patterns/)).toBeInTheDocument();
    expect(screen.getByText(/Warnings never block install/i)).toBeInTheDocument();
  });

  it('tells the owner a frozen copy is used when a pack is unavailable', async () => {
    vi.mocked(profilesApi.compile).mockResolvedValue(
      compileResult([
        {
          level: 'warning',
          code: 'pack_unavailable',
          message:
            "Pack 'QA / Test Engineer' (abcd1234) is no longer available to you; using a frozen copy captured at 2026-01-01.",
        },
      ]),
    );

    renderSetup();

    expect(await screen.findByText(/is no longer available/i)).toBeInTheDocument();
    expect(screen.getAllByText(/QA \/ Test Engineer/).length).toBeGreaterThan(0);
    expect(screen.getByText(/using a frozen copy/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Keep frozen/i })).toBeInTheDocument();
    expect(screen.getByRole('link', { name: /Customize a copy/i })).toBeInTheDocument();
  });

  it('does not claim a frozen copy for an owner when the pack was skipped', async () => {
    vi.mocked(profilesApi.compile).mockResolvedValue(
      compileResult([
        {
          level: 'warning',
          code: 'pack_unavailable',
          message:
            "Pack 'QA / Test Engineer' (abcd1234) is not available to you; it was skipped.",
        },
      ]),
    );

    renderSetup();

    expect(await screen.findByText(/skipped in this setup/i)).toBeInTheDocument();
    expect(screen.queryByText(/frozen/i)).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /Keep frozen/i })).not.toBeInTheDocument();
  });

  it('never claims frozen content to a non-owner viewing a public setup', async () => {
    vi.mocked(profilesApi.get).mockResolvedValue({
      ...profile,
      owner_id: 'someone-else',
      is_public: true,
    });
    vi.mocked(profilesApi.compile).mockResolvedValue(
      compileResult([
        {
          level: 'warning',
          code: 'pack_unavailable',
          message: "Pack 'abcd1234' is not available to you; it was skipped.",
        },
      ]),
    );

    renderSetup();

    expect(
      await screen.findByText(/is no longer available/i),
    ).toBeInTheDocument();
    expect(screen.getByText(/skipped in this setup/i)).toBeInTheDocument();
    expect(screen.queryByText(/frozen/i)).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /Keep frozen/i })).not.toBeInTheDocument();
  });
});
