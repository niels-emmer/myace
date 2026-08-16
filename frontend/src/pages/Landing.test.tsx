import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter } from 'react-router-dom';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import Landing from './Landing';
import { AuthProvider } from '../contexts/AuthContext';
import { authApi, demoApi } from '../lib/api';
import type { DemoCompileResult } from '../types';

vi.mock('../lib/api', () => ({
  authApi: {
    me: vi.fn(),
  },
  demoApi: {
    compile: vi.fn(),
  },
}));

function renderLanding() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={['/welcome']}>
        <AuthProvider>
          <Landing />
        </AuthProvider>
      </MemoryRouter>
    </QueryClientProvider>
  );
}

describe('Landing page', () => {
  beforeEach(() => {
    vi.mocked(authApi.me).mockRejectedValue(new Error('not authenticated'));
  });

  it('renders the pitch and a pre-filled demo textarea with no auth required', async () => {
    renderLanding();

    expect(await screen.findByText(/Write your AI agent rules once/i)).toBeInTheDocument();
    const textarea = screen.getByRole('textbox') as HTMLTextAreaElement;
    expect(textarea.value).toContain('## Formatting');

    expect(screen.getByRole('link', { name: /Log in/i })).toHaveAttribute('href', '/login');
    expect(screen.getByRole('link', { name: /Sign up/i })).toHaveAttribute(
      'href',
      '/login?mode=register'
    );
  });

  it('compiles the demo markdown and shows per-target output on click', async () => {
    const result: DemoCompileResult = {
      artifact_count: 2,
      targets: {
        'claude-code': { 'CLAUDE.md': '# Rules\n\n## Formatting\n\nUse 2-space indentation.\n' },
        cursor: { '.cursor/rules/Formatting.mdc': '---\ndescription: x\n---\nUse 2-space.\n' },
        opencode: { 'AGENTS.md': '# OpenCode Rules\n\n## Formatting\n' },
      },
    };
    vi.mocked(demoApi.compile).mockResolvedValue(result);

    renderLanding();
    await screen.findByText(/Write your AI agent rules once/i);

    fireEvent.click(screen.getByRole('button', { name: /Compile/i }));

    expect(await screen.findByText('CLAUDE.md')).toBeInTheDocument();
    expect(demoApi.compile).toHaveBeenCalledWith(expect.stringContaining('## Formatting'));

    fireEvent.click(screen.getByRole('button', { name: /Cursor/i }));
    await waitFor(() =>
      expect(screen.getByText('.cursor/rules/Formatting.mdc')).toBeInTheDocument()
    );
  });

  it('surfaces a compile error without crashing', async () => {
    vi.mocked(demoApi.compile).mockRejectedValue(new Error('markdown must be at most 20480 bytes'));

    renderLanding();
    await screen.findByText(/Write your AI agent rules once/i);
    fireEvent.click(screen.getByRole('button', { name: /Compile/i }));

    expect(await screen.findByText(/markdown must be at most 20480 bytes/i)).toBeInTheDocument();
  });
});
