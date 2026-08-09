import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter } from 'react-router-dom';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import ImportPage from './ImportPage';

function renderImportPage() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>
        <ImportPage />
      </MemoryRouter>
    </QueryClientProvider>
  );
}

describe('ImportPage local companion detection', () => {
  beforeEach(() => {
    vi.stubGlobal(
      'location',
      new URL('https://myace.example.com/import') as unknown as Location
    );
  });

  it('shows setup instructions with the real origin when the companion is unreachable', async () => {
    globalThis.fetch = vi.fn().mockRejectedValue(new Error('connection refused')) as unknown as typeof fetch;

    renderImportPage();
    fireEvent.change(screen.getByPlaceholderText('~/.config/opencode'), {
      target: { value: '~/.config/opencode' },
    });

    expect(
      await screen.findByText(/Local scanner not detected\. See setup steps below\./i)
    ).toBeInTheDocument();

    expect(
      screen.getAllByText(
        (_, node) =>
          node?.tagName === 'CODE' &&
          node.textContent ===
            'myace login --server https://myace.example.com --token <token-from-Settings>'
      ).length
    ).toBeGreaterThan(0);

    const scanButton = screen.getByRole('button', { name: /Scan Resources/i });
    expect(scanButton).toBeDisabled();
  });

  it('enables scanning once the companion server responds healthy', async () => {
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ status: 'ok', server: 'https://myace.example.com' }),
    }) as unknown as typeof fetch;

    renderImportPage();
    fireEvent.change(screen.getByPlaceholderText('~/.config/opencode'), {
      target: { value: '~/.config/opencode' },
    });

    expect(await screen.findByText(/Local scanner detected/i)).toBeInTheDocument();
    expect(
      screen.queryByText(/Local scanner not detected\. See setup steps below\./i)
    ).not.toBeInTheDocument();

    const scanButton = screen.getByRole('button', { name: /Scan Resources/i });
    await waitFor(() => expect(scanButton).toBeEnabled());
  });
});
