import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import TargetExporter from './TargetExporter';
import { profilesApi } from '../lib/api';
import { fetchCompanionHealth, installsApi } from '../lib/setupApi';
import type { Profile, CompileResult } from '../types';

vi.mock('../lib/api', () => ({
  profilesApi: {
    get: vi.fn(),
    compile: vi.fn(),
  },
}));

vi.mock('../lib/setupApi', async () => {
  const actual = await vi.importActual<typeof import('../lib/setupApi')>('../lib/setupApi');
  return {
    ...actual,
    installsApi: { list: vi.fn(), claim: vi.fn() },
    fetchCompanionHealth: vi.fn(),
  };
});

const mockProfile: Profile = {
  id: 'profile-1',
  owner_id: 'owner-1',
  name: 'my-defaults',
  base_collection_id: 'collection-1',
  additional_collection_ids: [],
  disabled_artifact_ids: [],
  target_frameworks: ['claude-code', 'opencode'],
  is_public: false,
  version: 1,
  created_at: '2026-01-01T00:00:00Z',
  updated_at: '2026-01-01T00:00:00Z',
};

const mockCompileResult: CompileResult = {
  profile_id: 'profile-1',
  profile_name: 'my-defaults',
  target: 'claude-code',
  artifact_count: 1,
  files: { 'CLAUDE.md': '# Agents' },
  compiled_hash: 'test-compiled-hash',
};

const claim = {
  id: 'claim-1',
  profile_id: 'profile-1',
  target: 'claude-code',
  location: 'machine' as const,
  method: 'zip',
  created_at: '2026-01-01T00:00:00Z',
  updated_at: '2026-01-01T00:00:00Z',
};

function renderInstall(path = '/setups/profile-1/install') {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={[path]}>
        <Routes>
          <Route path="/setups/:id/install" element={<TargetExporter />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

async function waitForProfile() {
  await screen.findByRole('heading', { name: /Install “my-defaults”/ });
}

describe('TargetExporter install panel', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(profilesApi.get).mockResolvedValue(mockProfile);
    vi.mocked(profilesApi.compile).mockResolvedValue(mockCompileResult);
    vi.mocked(installsApi.list).mockResolvedValue([]);
    vi.mocked(installsApi.claim).mockResolvedValue(claim);
    vi.mocked(fetchCompanionHealth).mockResolvedValue({
      status: 'ok',
      server: 'https://myace.example.com',
      apply: { supported: false, targets: [], machine_targets: [] },
      baseUrl: 'http://127.0.0.1:8765',
    });
    Object.defineProperty(navigator, 'clipboard', {
      value: { writeText: vi.fn().mockResolvedValue(undefined) },
      configurable: true,
    });
    globalThis.URL.createObjectURL = vi.fn(() => 'blob:mock-url');
    globalThis.URL.revokeObjectURL = vi.fn();
    vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(() => {});
  });

  it('uses the setup’s own frameworks and defaults to the machine location', async () => {
    renderInstall();
    await waitForProfile();

    expect(screen.getByRole('option', { name: /claude-code/ })).toBeInTheDocument();
    expect(screen.queryByRole('option', { name: /cursor/ })).not.toBeInTheDocument();
    // Machine is the default when the framework supports it.
    expect(screen.getByText('~/.claude')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Download .zip' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Download' })).toBeInTheDocument();
  });

  it('previews files without recording an install claim', async () => {
    renderInstall();
    await waitForProfile();

    fireEvent.click(screen.getByRole('button', { name: /Preview files/i }));

    expect(await screen.findByText('CLAUDE.md')).toBeInTheDocument();
    expect(profilesApi.compile).toHaveBeenCalledWith({
      profile_id: 'profile-1',
      target: 'claude-code',
    });
    expect(installsApi.claim).not.toHaveBeenCalled();
  });

  it('records a zip install claim on download, never a verification', async () => {
    const blob = new Blob(['fake zip bytes'], { type: 'application/zip' });
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: true,
      blob: () => Promise.resolve(blob),
    }) as unknown as typeof fetch;

    renderInstall();
    await waitForProfile();

    fireEvent.click(screen.getByRole('button', { name: 'Download .zip' }));

    await waitFor(() =>
      expect(installsApi.claim).toHaveBeenCalledWith('profile-1', {
        target: 'claude-code',
        location: 'machine',
        method: 'zip',
      }),
    );
    expect(globalThis.URL.createObjectURL).toHaveBeenCalledWith(blob);
  });

  it('records a CLI claim when the pull command is copied', async () => {
    renderInstall();
    await waitForProfile();

    fireEvent.click(screen.getByRole('button', { name: 'CLI' }));
    fireEvent.click(screen.getByRole('button', { name: /Copy CLI command/i }));

    await waitFor(() =>
      expect(installsApi.claim).toHaveBeenCalledWith('profile-1', {
        target: 'claude-code',
        location: 'machine',
        method: 'cli',
      }),
    );
    expect(navigator.clipboard.writeText).toHaveBeenCalledWith(
      "myace pull --profile 'my-defaults' --target 'claude-code'",
    );
  });

  it('resets preview state when the framework changes', async () => {
    renderInstall();
    await waitForProfile();

    fireEvent.click(screen.getByRole('button', { name: /Preview files/i }));
    expect(await screen.findByText('CLAUDE.md')).toBeInTheDocument();

    fireEvent.change(screen.getByLabelText('Framework'), {
      target: { value: 'opencode' },
    });

    await waitFor(() => expect(screen.queryByText('CLAUDE.md')).not.toBeInTheDocument());
  });

  it('hides direct install entirely when the companion does not advertise apply', async () => {
    renderInstall();
    await waitForProfile();

    await screen.findByRole('button', { name: 'Download' });
    expect(
      screen.queryByRole('button', { name: 'Install directly' }),
    ).not.toBeInTheDocument();
    expect(screen.queryByText(/needs the local companion/i)).not.toBeInTheDocument();
  });
});
