import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter } from 'react-router-dom';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import TargetExporter from './TargetExporter';
import { profilesApi, adaptersApi } from '../lib/api';
import type { Profile, AdapterInfo, CompileResult } from '../types';

vi.mock('../lib/api', () => ({
  profilesApi: {
    list: vi.fn(),
    compile: vi.fn(),
  },
  adaptersApi: {
    list: vi.fn(),
  },
}));

const mockProfile: Profile = {
  id: 'profile-1',
  owner_id: 'owner-1',
  name: 'my-defaults',
  base_collection_id: 'collection-1',
  additional_collection_ids: [],
  disabled_artifact_ids: [],
  is_public: false,
  version: 1,
  created_at: '2026-01-01T00:00:00Z',
  updated_at: '2026-01-01T00:00:00Z',
};

const mockAdapter: AdapterInfo = {
  name: 'opencode',
  description: 'OpenCode adapter',
  targets: ['opencode'],
  enabled: true,
};

const mockAdapterTwo: AdapterInfo = {
  name: 'goose',
  description: 'Goose adapter',
  targets: ['goose'],
  enabled: true,
};

const mockCompileResult: CompileResult = {
  profile_id: 'profile-1',
  profile_name: 'my-defaults',
  target: 'opencode',
  artifact_count: 1,
  files: { 'AGENTS.md': '# Agents' },
  compiled_hash: 'test-compiled-hash',
};

const mockCompileResultWithWarnings: CompileResult = {
  ...mockCompileResult,
  warnings: [
    {
      level: 'warning',
      code: 'name_collision',
      message:
        "Artifact 'security-checklist' is defined in both 'base-collection' and " +
        "'additional-collection'; 'additional-collection' wins.",
    },
  ],
};

function renderWithQueryClient() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>
        <TargetExporter />
      </MemoryRouter>
    </QueryClientProvider>
  );
}

async function selectProfile() {
  // Wait for the profile option to actually be in the DOM before firing
  // change — jsdom silently no-ops a select value change to an option that
  // doesn't exist yet, which happens if we fire before the query resolves.
  await screen.findByRole('option', { name: 'my-defaults' });
  const [profileSelect] = screen.getAllByRole('combobox');
  fireEvent.change(profileSelect, { target: { value: 'profile-1' } });
  await waitFor(() => expect(profileSelect).toHaveValue('profile-1'));

  const compileButton = screen.getByRole('button', { name: /Compile/i });
  await waitFor(() => expect(compileButton).toBeEnabled());
  fireEvent.click(compileButton);
  await waitFor(() => expect(profilesApi.compile).toHaveBeenCalled());
}

describe('TargetExporter zip download', () => {
  beforeEach(() => {
    vi.mocked(profilesApi.list).mockResolvedValue([mockProfile]);
    vi.mocked(adaptersApi.list).mockResolvedValue([mockAdapter]);
    vi.mocked(profilesApi.compile).mockResolvedValue(mockCompileResult);

    globalThis.URL.createObjectURL = vi.fn(() => 'blob:mock-url');
    globalThis.URL.revokeObjectURL = vi.fn();
  });

  it('downloads a zip via fetch and triggers a browser save, without going through profilesApi', async () => {
    const blob = new Blob(['fake zip bytes'], { type: 'application/zip' });
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      blob: () => Promise.resolve(blob),
    });
    globalThis.fetch = fetchMock as unknown as typeof fetch;

    const clickSpy = vi
      .spyOn(HTMLAnchorElement.prototype, 'click')
      .mockImplementation(() => {});

    renderWithQueryClient();
    await selectProfile();

    const downloadButton = await screen.findByRole('button', { name: /Download as \.zip/i });
    fireEvent.click(downloadButton);

    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(1));
    expect(fetchMock).toHaveBeenCalledWith(
      '/api/v1/profiles/compile/zip',
      expect.objectContaining({
        method: 'POST',
        credentials: 'same-origin',
        body: JSON.stringify({ profile_id: 'profile-1', target: 'opencode' }),
      })
    );

    await waitFor(() => expect(clickSpy).toHaveBeenCalled());
    expect(globalThis.URL.createObjectURL).toHaveBeenCalledWith(blob);
    // Revocation is deferred (see TargetExporter.tsx) so Safari's native
    // "Save As" dialog has time to read the blob before the URL dies.
    await waitFor(() => expect(globalThis.URL.revokeObjectURL).toHaveBeenCalledWith('blob:mock-url'), {
      timeout: 2000,
    });

    clickSpy.mockRestore();
  });

  it('shows no warnings panel when the compile response has no warnings', async () => {
    renderWithQueryClient();
    await selectProfile();

    await screen.findByText(/Output — 1 artifacts/i);
    expect(screen.queryByText(/warning/i)).not.toBeInTheDocument();
  });

  it('downloads the zip for the compiled result, not the live target dropdown, if the dropdown changes after Compile', async () => {
    // Regression test: the download previously read `selectedTarget` (live
    // dropdown state) instead of `result.target` (what was actually
    // compiled and is displayed). Changing the dropdown after compiling —
    // without recompiling — must not change what the zip download requests.
    vi.mocked(adaptersApi.list).mockResolvedValue([mockAdapter, mockAdapterTwo]);

    const blob = new Blob(['fake zip bytes'], { type: 'application/zip' });
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      blob: () => Promise.resolve(blob),
    });
    globalThis.fetch = fetchMock as unknown as typeof fetch;
    vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(() => {});

    renderWithQueryClient();
    await selectProfile();

    // result.target is 'opencode' (from mockCompileResult). Now change the
    // target dropdown to 'goose' WITHOUT clicking Compile again.
    const targetSelect = screen.getAllByRole('combobox')[1];
    fireEvent.change(targetSelect, { target: { value: 'goose' } });
    await waitFor(() => expect(targetSelect).toHaveValue('goose'));

    fireEvent.click(await screen.findByRole('button', { name: /Download as \.zip/i }));

    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(1));
    expect(fetchMock).toHaveBeenCalledWith(
      '/api/v1/profiles/compile/zip',
      expect.objectContaining({
        body: JSON.stringify({ profile_id: 'profile-1', target: 'opencode' }),
      })
    );
  });

  it('shows an error message when the zip download fails', async () => {
    globalThis.fetch = vi.fn().mockResolvedValue({ ok: false, status: 500 }) as unknown as typeof fetch;

    renderWithQueryClient();
    await selectProfile();

    fireEvent.click(await screen.findByRole('button', { name: /Download as \.zip/i }));

    expect(await screen.findByText(/Could not download the zip/i)).toBeInTheDocument();
  });
});

describe('TargetExporter compile warnings panel', () => {
  beforeEach(() => {
    vi.mocked(profilesApi.list).mockResolvedValue([mockProfile]);
    vi.mocked(adaptersApi.list).mockResolvedValue([mockAdapter]);
  });

  it('renders a dismissible warnings panel above the file output when warnings are present', async () => {
    vi.mocked(profilesApi.compile).mockResolvedValue(mockCompileResultWithWarnings);

    renderWithQueryClient();
    await selectProfile();

    expect(await screen.findByText(/1 warning from compilation/i)).toBeInTheDocument();
    expect(screen.getByText(/base-collection/)).toBeInTheDocument();
    expect(screen.getByText(/additional-collection/)).toBeInTheDocument();

    const dismissButton = screen.getByRole('button', { name: /Dismiss warnings/i });
    fireEvent.click(dismissButton);

    expect(screen.queryByText(/1 warning from compilation/i)).not.toBeInTheDocument();
    // Dismissing the panel must not remove the compiled output itself.
    expect(screen.getByText('AGENTS.md')).toBeInTheDocument();
  });

  it('re-shows warnings on a fresh compile even after a previous dismissal', async () => {
    vi.mocked(profilesApi.compile).mockResolvedValue(mockCompileResultWithWarnings);

    renderWithQueryClient();
    await selectProfile();

    fireEvent.click(await screen.findByRole('button', { name: /Dismiss warnings/i }));
    expect(screen.queryByText(/1 warning from compilation/i)).not.toBeInTheDocument();

    // Recompile (same button, now labeled "Compile" again since loading reset).
    fireEvent.click(screen.getByRole('button', { name: /Compile/i }));

    expect(await screen.findByText(/1 warning from compilation/i)).toBeInTheDocument();
  });
});
