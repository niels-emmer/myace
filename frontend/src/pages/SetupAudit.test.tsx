import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter } from 'react-router-dom';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import SetupAudit from './SetupAudit';

function renderSetupAudit() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>
        <SetupAudit />
      </MemoryRouter>
    </QueryClientProvider>
  );
}

describe('SetupAudit companion detection', () => {
  beforeEach(() => {
    vi.stubGlobal(
      'location',
      new URL('https://myace.example.com/setup-audit') as unknown as Location
    );
  });

  it('shows setup instructions when the companion is unreachable', async () => {
    globalThis.fetch = vi.fn().mockRejectedValue(new Error('connection refused')) as unknown as typeof fetch;

    renderSetupAudit();

    expect(
      await screen.findByText(/Local scanner not detected\. See setup steps below\./i)
    ).toBeInTheDocument();

    const runButton = screen.getByRole('button', { name: /Run Audit/i });
    expect(runButton).toBeDisabled();
  });

  it('enables running the audit once the companion server responds healthy', async () => {
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ status: 'ok', server: 'https://myace.example.com' }),
    }) as unknown as typeof fetch;

    renderSetupAudit();

    expect(await screen.findByText(/Local scanner detected/i)).toBeInTheDocument();

    const runButton = screen.getByRole('button', { name: /Run Audit/i });
    await waitFor(() => expect(runButton).toBeEnabled());
  });
});

describe('SetupAudit result rendering', () => {
  beforeEach(() => {
    vi.stubGlobal(
      'location',
      new URL('https://myace.example.com/setup-audit') as unknown as Location
    );
  });

  it('renders score, gaps, and duplicates from a completed audit', async () => {
    const healthResponse = {
      ok: true,
      json: () => Promise.resolve({ status: 'ok', server: 'https://myace.example.com' }),
    };
    const auditResponse = {
      ok: true,
      json: () =>
        Promise.resolve({
          path: '~',
          score: 72,
          targets: {
            'claude-code': { detected: true, artifact_count: 2, artifacts: [] },
            cursor: { detected: true, artifact_count: 1, artifacts: [] },
          },
          gaps: [
            {
              artifact_type: 'skill',
              name: 'security-checklist',
              present_in: ['claude-code'],
              missing_from: ['cursor'],
            },
          ],
          duplicates: [
            { target: 'claude-code', artifact_type: 'agent', name: 'reviewer', count: 2 },
          ],
        }),
    };

    globalThis.fetch = vi
      .fn()
      .mockResolvedValueOnce(healthResponse)
      .mockResolvedValue(auditResponse) as unknown as typeof fetch;

    renderSetupAudit();

    const runButton = await screen.findByRole('button', { name: /Run Audit/i });
    await waitFor(() => expect(runButton).toBeEnabled());
    fireEvent.click(runButton);

    expect(await screen.findByText('72')).toBeInTheDocument();
    expect(screen.getByText('security-checklist')).toBeInTheDocument();
    expect(screen.getByText(/Coverage gaps/i)).toBeInTheDocument();
    expect(screen.getByText(/Duplicate names/i)).toBeInTheDocument();
    expect(screen.getByText(/Defined 2 times under claude-code\./i)).toBeInTheDocument();
  });
});
