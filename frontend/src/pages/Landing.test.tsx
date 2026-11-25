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

vi.mock('../lib/packApi', () => ({
  packApi: {
    listCommunity: vi.fn(),
  },
}));

import { packApi } from '../lib/packApi';

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
    vi.mocked(packApi.listCommunity).mockResolvedValue({ items: [], total: 0 });
  });

  it('renders the pitch and a pre-filled demo textarea with no auth required', async () => {
    renderLanding();

    expect(await screen.findByText(/Write your AI agent rules once/i)).toBeInTheDocument();
    const textarea = screen.getByRole('textbox') as HTMLTextAreaElement;
    expect(textarea.value).toContain('## Formatting');

    expect(screen.getByRole('link', { name: /Log in/i })).toHaveAttribute('href', '/login');
    expect(screen.getAllByRole('link', { name: 'Sign up' })[0]).toHaveAttribute(
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

  it('shows the four-step story and CTAs to browse packs and set up', async () => {
    renderLanding();
    await screen.findByText(/Write your AI agent rules once/i);

    expect(screen.getAllByText('Browse packs').length).toBeGreaterThan(0);
    expect(screen.getByText('Build a setup')).toBeInTheDocument();
    expect(screen.getByText('Install everywhere')).toBeInTheDocument();
    expect(screen.getByText('Publish')).toBeInTheDocument();

    expect(screen.getAllByRole('link', { name: /Browse packs/i })[0]).toHaveAttribute(
      'href',
      '/packs',
    );
    expect(screen.getByRole('link', { name: 'Create a free account' })).toHaveAttribute(
      'href',
      '/login?mode=register',
    );
  });

  it('renders featured packs from the public community endpoint', async () => {
    vi.mocked(packApi.listCommunity).mockResolvedValue({
      items: [
        {
          id: 'starter-1',
          owner_id: 'starter',
          name: 'Software Engineer',
          description: 'A complete starting point.',
          collection_type: 'base',
          artifact_count: 20,
          download_count: 1200,
          published: true,
          is_starter_pack: true,
          avg_rating: 4.8,
          rating_count: 12,
          moderation_status: 'approved',
          created_at: '2026-01-01T00:00:00Z',
          updated_at: '2026-01-01T00:00:00Z',
        },
      ],
      total: 1,
    });

    renderLanding();
    expect(await screen.findByText('Software Engineer')).toBeInTheDocument();
    expect(screen.getByRole('link', { name: /Software Engineer/ })).toHaveAttribute(
      'href',
      '/packs/starter-1',
    );
    expect(screen.getByText('Starter')).toBeInTheDocument();
    expect(screen.getAllByText('All 12 frameworks').length).toBeGreaterThan(0);
    expect(screen.getByText('1.2k uses')).toBeInTheDocument();
  });

  it('advertises the anonymous, read-only MCP endpoint between the pack grid and the demo', async () => {
    const writeText = vi.fn().mockResolvedValue(undefined);
    Object.defineProperty(navigator, 'clipboard', {
      value: { writeText },
      configurable: true,
    });

    renderLanding();
    await screen.findByText(/Write your AI agent rules once/i);

    const agentHeading = screen.getByRole('heading', { name: /Point your agent at the library/i });
    expect(screen.getByText(/read-only by design/i)).toBeInTheDocument();

    // Placement: after "Start from a proven pack", before "See the translation".
    const demoHeading = screen.getByRole('heading', { name: /See the translation/i });
    expect(
      agentHeading.compareDocumentPosition(demoHeading) & Node.DOCUMENT_POSITION_FOLLOWING
    ).toBeTruthy();
    const featuredHeading = screen.getByRole('heading', { name: /Start from a proven pack/i });
    expect(
      featuredHeading.compareDocumentPosition(agentHeading) & Node.DOCUMENT_POSITION_FOLLOWING
    ).toBeTruthy();

    const endpoint = `${window.location.origin}/mcp`;
    const command = `claude mcp add --transport http myace ${endpoint}`;
    expect(screen.getAllByText(endpoint, { exact: false }).length).toBeGreaterThan(0);

    fireEvent.click(screen.getByRole('button', { name: /copy MCP endpoint/i }));
    await waitFor(() => expect(writeText).toHaveBeenCalledWith(endpoint));

    fireEvent.click(screen.getByRole('button', { name: /copy Claude Code command/i }));
    await waitFor(() => expect(writeText).toHaveBeenCalledWith(command));
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
      name: 'Sign up free — start building',
    });
    expect(cta).toHaveAttribute('href', '/login?mode=register');

    const lastFeature = screen.getByText('12 target frameworks');
    expect(
      lastFeature.compareDocumentPosition(cta) & Node.DOCUMENT_POSITION_FOLLOWING
    ).toBeTruthy();
  });
});
