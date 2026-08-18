import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter } from 'react-router-dom';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import NewArtifactRule from './NewArtifactRule';

const mockNavigate = vi.fn();
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom');
  return {
    ...actual,
    useParams: () => ({ id: 'test-collection-id' }),
    useNavigate: () => mockNavigate,
  };
});

vi.mock('../lib/api', () => ({
  collectionsApi: {
    createArtifact: vi.fn(),
  },
  adaptersApi: {
    list: vi.fn(),
  },
}));

import { collectionsApi, adaptersApi } from '../lib/api';

function renderPage() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>
        <NewArtifactRule />
      </MemoryRouter>
    </QueryClientProvider>
  );
}

describe('NewArtifactRule', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    (adaptersApi.list as ReturnType<typeof vi.fn>).mockResolvedValue([
      { name: 'claude-code', description: '', targets: ['claude-code'], enabled: true },
      { name: 'opencode', description: '', targets: ['opencode'], enabled: true },
    ]);
  });

  it('blocks submit and shows an error when name is empty', async () => {
    renderPage();
    const bodyInput = await screen.findByPlaceholderText('Markdown content for this rule...');
    fireEvent.change(bodyInput, { target: { value: 'some body' } });
    fireEvent.click(screen.getByRole('button', { name: /^Add rule$/ }));

    expect(await screen.findByText('Name is required.')).toBeInTheDocument();
    expect(collectionsApi.createArtifact).not.toHaveBeenCalled();
  });

  it('blocks submit and shows an error when body is empty', async () => {
    renderPage();
    fireEvent.change(screen.getByPlaceholderText(/No trailing whitespace/i), {
      target: { value: 'My Rule' },
    });
    fireEvent.click(screen.getByRole('button', { name: /^Add rule$/ }));

    expect(await screen.findByText('Body is required.')).toBeInTheDocument();
    expect(collectionsApi.createArtifact).not.toHaveBeenCalled();
  });

  it('blocks submit on a malformed version', async () => {
    renderPage();
    fireEvent.change(screen.getByPlaceholderText(/No trailing whitespace/i), {
      target: { value: 'My Rule' },
    });
    fireEvent.change(screen.getByPlaceholderText(/Markdown content/i), {
      target: { value: 'body text' },
    });
    fireEvent.change(screen.getByDisplayValue('1.0.0'), { target: { value: 'v1' } });
    fireEvent.click(screen.getByRole('button', { name: /^Add rule$/ }));

    expect(
      await screen.findByText(/Version must look like 1\.0\.0/i)
    ).toBeInTheDocument();
    expect(collectionsApi.createArtifact).not.toHaveBeenCalled();
  });

  it('creates a rule artifact with defaults and navigates back on success', async () => {
    (collectionsApi.createArtifact as ReturnType<typeof vi.fn>).mockResolvedValue({
      id: 'new-art-1',
    });
    renderPage();

    fireEvent.change(screen.getByPlaceholderText(/No trailing whitespace/i), {
      target: { value: 'My New Rule' },
    });
    fireEvent.change(screen.getByPlaceholderText(/Markdown content/i), {
      target: { value: 'Do the thing.' },
    });
    fireEvent.click(screen.getByRole('button', { name: /^Add rule$/ }));

    await waitFor(() => {
      expect(collectionsApi.createArtifact).toHaveBeenCalledWith('test-collection-id', {
        artifact_type: 'rule',
        name: 'My New Rule',
        description: undefined,
        version: '1.0.0',
        priority: 50,
        target_compatibility: [],
        tags: [],
        body: 'Do the thing.',
        file_path: 'AGENTS.md',
      });
    });

    await waitFor(() => {
      expect(mockNavigate).toHaveBeenCalledWith('/collections/test-collection-id');
    });
  });

  it('splits comma-separated tags and trims whitespace', async () => {
    (collectionsApi.createArtifact as ReturnType<typeof vi.fn>).mockResolvedValue({
      id: 'new-art-1',
    });
    renderPage();

    fireEvent.change(screen.getByPlaceholderText(/No trailing whitespace/i), {
      target: { value: 'My New Rule' },
    });
    fireEvent.change(screen.getByPlaceholderText(/Markdown content/i), {
      target: { value: 'Do the thing.' },
    });
    fireEvent.change(screen.getByPlaceholderText(/python, testing/i), {
      target: { value: ' python ,  testing ,,' },
    });
    fireEvent.click(screen.getByRole('button', { name: /^Add rule$/ }));

    await waitFor(() => {
      expect(collectionsApi.createArtifact).toHaveBeenCalledWith(
        'test-collection-id',
        expect.objectContaining({ tags: ['python', 'testing'] })
      );
    });
  });

  it('includes checked targets in the submission', async () => {
    (collectionsApi.createArtifact as ReturnType<typeof vi.fn>).mockResolvedValue({
      id: 'new-art-1',
    });
    renderPage();

    fireEvent.change(screen.getByPlaceholderText(/No trailing whitespace/i), {
      target: { value: 'My New Rule' },
    });
    fireEvent.change(screen.getByPlaceholderText(/Markdown content/i), {
      target: { value: 'Do the thing.' },
    });
    const opencodeCheckbox = await screen.findByRole('checkbox', { name: 'opencode' });
    fireEvent.click(opencodeCheckbox);
    fireEvent.click(screen.getByRole('button', { name: /^Add rule$/ }));

    await waitFor(() => {
      expect(collectionsApi.createArtifact).toHaveBeenCalledWith(
        'test-collection-id',
        expect.objectContaining({ target_compatibility: ['opencode'] })
      );
    });
  });

  it('shows a server error message when creation fails', async () => {
    (collectionsApi.createArtifact as ReturnType<typeof vi.fn>).mockRejectedValue(
      new Error('Collection not found')
    );
    renderPage();

    fireEvent.change(screen.getByPlaceholderText(/No trailing whitespace/i), {
      target: { value: 'My New Rule' },
    });
    fireEvent.change(screen.getByPlaceholderText(/Markdown content/i), {
      target: { value: 'Do the thing.' },
    });
    fireEvent.click(screen.getByRole('button', { name: /^Add rule$/ }));

    expect(await screen.findByText('Collection not found')).toBeInTheDocument();
    expect(mockNavigate).not.toHaveBeenCalled();
  });

  it('has a Cancel link back to the collection detail page', async () => {
    renderPage();
    const cancelLink = await screen.findByRole('link', { name: /Cancel/i });
    expect(cancelLink).toHaveAttribute('href', '/collections/test-collection-id');
  });
});
