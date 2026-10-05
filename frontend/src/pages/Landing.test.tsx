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

  it('shows the large centered brand mark above the headline', async () => {
    renderLanding();
    const headline = await screen.findByRole('heading', {
      level: 1,
      name: /Write your AI agent rules once/i,
    });

    // The hero title is a separate element from the header's small wordmark.
    const heroTitle = screen.getAllByText('MyACE').find((el) => el.tagName === 'P');
    expect(heroTitle).toBeDefined();
    // It sits before the headline in document order, in a centered column.
    expect(
      heroTitle!.compareDocumentPosition(headline) & Node.DOCUMENT_POSITION_FOLLOWING
    ).toBeTruthy();
    expect(heroTitle!.parentElement).toHaveClass('flex', 'flex-col', 'items-center');
    expect(heroTitle!.parentElement!.querySelector('img[src="/logo.png"]')).not.toBeNull();
  });

  it('ends with a call to action that leads to signup, after the feature blocks', async () => {
    renderLanding();
    const cta = await screen.findByRole('link', {
      name: 'Accounts are free, register today and start building!',
    });
    expect(cta).toHaveAttribute('href', '/login?mode=register');

    const lastFeature = screen.getByText('12 target frameworks');
    expect(
      lastFeature.compareDocumentPosition(cta) & Node.DOCUMENT_POSITION_FOLLOWING
    ).toBeTruthy();
  });
});
