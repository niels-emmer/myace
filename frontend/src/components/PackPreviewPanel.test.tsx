import { fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import PackPreviewPanel from './PackPreviewPanel';
import { PreviewError, packApi } from '../lib/packApi';
import { probeMcpAvailability } from '../lib/mcp';

vi.mock('../lib/packApi', async () => {
  const actual = await vi.importActual<typeof import('../lib/packApi')>('../lib/packApi');
  return {
    ...actual,
    packApi: { getFrameworks: vi.fn(), previewInstall: vi.fn() },
  };
});
vi.mock('../lib/mcp', () => ({ probeMcpAvailability: vi.fn() }));

const preview = (target: string) => ({
  subject: 'pack',
  pack_id: 'pack-1',
  target,
  artifact_count: 2,
  compiled_hash: 'abc',
  warnings: [],
  files: {
    'CLAUDE.md': '# Rules\n\n<script>alert(1)</script>',
    '.claude/agents/reviewer.md': 'Read-only reviewer',
  },
});

function renderPanel() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={queryClient}>
      <PackPreviewPanel packId="pack-1" />
    </QueryClientProvider>,
  );
}

describe('PackPreviewPanel', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(packApi.getFrameworks).mockResolvedValue(['claude-code', 'opencode', 'cursor']);
    vi.mocked(packApi.previewInstall).mockImplementation(async (_id, target) => preview(target));
    vi.mocked(probeMcpAvailability).mockResolvedValue(true);
  });

  it('previews the default framework and lists its files', async () => {
    renderPanel();

    const files = within(await screen.findByRole('navigation', { name: 'Compiled files' }));
    expect(files.getByRole('button', { name: '.claude/agents/reviewer.md' })).toBeInTheDocument();
    expect(files.getByRole('button', { name: 'CLAUDE.md' })).toBeInTheDocument();
    expect(packApi.previewInstall).toHaveBeenCalledWith('pack-1', 'claude-code');
  });

  it('renders file text as text, never as markup', async () => {
    const { container } = renderPanel();

    // Opens on the top-level rules file, not the alphabetically first path.
    const pre = await screen.findByLabelText('Contents of CLAUDE.md');
    expect(pre.textContent).toContain('<script>alert(1)</script>');
    expect(container.querySelector('script')).toBeNull();

    fireEvent.click(screen.getByRole('button', { name: '.claude/agents/reviewer.md' }));
    await waitFor(() =>
      expect(pre).toHaveAttribute('aria-label', 'Contents of .claude/agents/reviewer.md'),
    );
  });

  it('refetches when the framework changes', async () => {
    renderPanel();
    await screen.findByRole('navigation', { name: 'Compiled files' });

    fireEvent.change(screen.getByLabelText('Framework'), { target: { value: 'cursor' } });

    await waitFor(() => expect(packApi.previewInstall).toHaveBeenCalledWith('pack-1', 'cursor'));
  });

  it('shows compile warnings', async () => {
    vi.mocked(packApi.previewInstall).mockResolvedValue({
      ...preview('claude-code'),
      warnings: [{ level: 'warning', code: 'permissions_not_enforced', message: 'Not enforced here' }],
    });
    renderPanel();

    expect(await screen.findByText('Not enforced here')).toBeInTheDocument();
    expect(screen.getByText('1 compile warning')).toBeInTheDocument();
  });

  it('explains a failure instead of showing an empty panel', async () => {
    vi.mocked(packApi.previewInstall).mockRejectedValue(
      new PreviewError(429, 'Too many requests right now. Try again in a minute.'),
    );
    renderPanel();

    expect(await screen.findByRole('alert')).toHaveTextContent(/Too many requests/);
  });

  it('offers a zip download and the agent install URL built from this origin', async () => {
    renderPanel();
    await screen.findByRole('navigation', { name: 'Compiled files' });

    expect(screen.getByRole('link', { name: /Download zip/ })).toHaveAttribute(
      'href',
      `${window.location.origin}/api/v1/collections/community/pack-1/install.md?target=claude-code&format=zip`,
    );
    expect(screen.getByText(/install\.md\?target=claude-code$/)).toBeInTheDocument();
  });

  it('shows the MCP command only when the MCP server is available', async () => {
    renderPanel();
    expect(await screen.findByText(/claude mcp add --transport http myace/)).toBeInTheDocument();
  });

  it('hides the MCP command when MCP is not enabled on this deployment', async () => {
    vi.mocked(probeMcpAvailability).mockResolvedValue(false);
    renderPanel();
    await screen.findByRole('navigation', { name: 'Compiled files' });

    expect(screen.queryByText(/claude mcp add/)).not.toBeInTheDocument();
  });
});
