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
};

const mockCompileResult: CompileResult = {
  profile_id: 'profile-1',
  profile_name: 'my-defaults',
  target: 'opencode',
  artifact_count: 1,
  files: { 'AGENTS.md': '# Agents' },
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
    expect(globalThis.URL.revokeObjectURL).toHaveBeenCalledWith('blob:mock-url');

    clickSpy.mockRestore();
  });

  it('shows an error message when the zip download fails', async () => {
    globalThis.fetch = vi.fn().mockResolvedValue({ ok: false, status: 500 }) as unknown as typeof fetch;

    renderWithQueryClient();
    await selectProfile();

    fireEvent.click(await screen.findByRole('button', { name: /Download as \.zip/i }));

    expect(await screen.findByText(/Could not download the zip/i)).toBeInTheDocument();
  });
});
