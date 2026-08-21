import { render, screen, fireEvent } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter, Routes, Route, useLocation } from 'react-router-dom';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import OrchestrationGallery from './OrchestrationGallery';
import { ThemeProvider } from '../contexts/ThemeContext';
import { collectionsApi } from '../lib/api';
import type { Collection, Artifact, CommunityCollectionsResponse } from '../types';

vi.mock('../lib/api', () => ({
  collectionsApi: {
    list: vi.fn(),
    listCommunity: vi.fn(),
    getArtifacts: vi.fn(),
  },
}));

// @xyflow/react's <ReactFlow> measures its container via ResizeObserver,
// which jsdom doesn't implement — a minimal stub is enough for it to
// mount without throwing.
class ResizeObserverStub {
  observe() {}
  unobserve() {}
  disconnect() {}
}
vi.stubGlobal('ResizeObserver', ResizeObserverStub);

function renderPage() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <ThemeProvider>
        <MemoryRouter>
          <OrchestrationGallery />
        </MemoryRouter>
      </ThemeProvider>
    </QueryClientProvider>
  );
}

const collection: Collection = {
  id: 'collection-1',
  owner_id: 'owner-1',
  name: 'software-engineer',
  git_url: 'seed://base/software-engineer',
  git_branch: 'main',
  collection_type: 'base',
  visibility: 'public',
  is_active: true,
  artifact_count: 2,
  download_count: 0,
  published: true,
  avg_rating: 0,
  rating_count: 0,
  moderation_status: 'approved',
  created_at: '2026-01-01T00:00:00Z',
  updated_at: '2026-01-01T00:00:00Z',
};

function makeAgent(overrides: Partial<Artifact>): Artifact {
  return {
    id: overrides.name ?? 'agent',
    collection_id: 'collection-1',
    artifact_type: 'agent',
    name: 'agent',
    version: '1.0.0',
    priority: 50,
    target_compatibility: ['claude-code'],
    tags: [],
    description: '',
    body: '',
    file_path: 'agents/agent.md',
    is_enabled: true,
    created_at: '2026-01-01T00:00:00Z',
    updated_at: '2026-01-01T00:00:00Z',
    ...overrides,
  };
}

const emptyCommunity: CommunityCollectionsResponse = { items: [], total: 0 };

function EditStateProbe() {
  const state = useLocation().state as { editRecipe?: { primary?: { name?: string } } } | null;
  return <span data-testid="edit-state">{state?.editRecipe?.primary?.name ?? 'none'}</span>;
}

describe('OrchestrationGallery', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('shows an empty state when no agent has mode:primary + handoff_to', async () => {
    (collectionsApi.list as ReturnType<typeof vi.fn>).mockResolvedValue([collection]);
    (collectionsApi.listCommunity as ReturnType<typeof vi.fn>).mockResolvedValue(emptyCommunity);
    (collectionsApi.getArtifacts as ReturnType<typeof vi.fn>).mockResolvedValue([
      makeAgent({ name: 'builder', tags: ['mode:subagent'], handoff_to: ['verifier'] }),
    ]);

    renderPage();

    expect(await screen.findByText(/No orchestration recipes found yet/i)).toBeInTheDocument();
  });

  it('renders a recipe card for a primary agent with handoff_to, and a flow diagram on selection', async () => {
    (collectionsApi.list as ReturnType<typeof vi.fn>).mockResolvedValue([collection]);
    (collectionsApi.listCommunity as ReturnType<typeof vi.fn>).mockResolvedValue(emptyCommunity);
    (collectionsApi.getArtifacts as ReturnType<typeof vi.fn>).mockResolvedValue([
      makeAgent({
        name: 'orchestrator',
        tags: ['mode:primary'],
        handoff_to: ['builder', 'verifier'],
        description: 'Routes work through the pipeline.',
      }),
      makeAgent({ name: 'builder', tags: ['mode:subagent'], handoff_to: ['verifier'] }),
      makeAgent({ name: 'verifier', tags: ['mode:subagent'], handoff_to: ['builder'] }),
    ]);

    renderPage();

    expect(await screen.findByText('Orchestrator')).toBeInTheDocument();
    expect(screen.getByText('software-engineer')).toBeInTheDocument();
    expect(screen.getByText('2 stages')).toBeInTheDocument();

    fireEvent.click(screen.getByText('Orchestrator'));

    // The diagram view renders one node per agent reached via handoff_to,
    // including the back-edge from verifier to builder.
    expect(await screen.findByText('Back to gallery')).toBeInTheDocument();
    expect(screen.getAllByText('Builder').length).toBeGreaterThan(0);
    expect(screen.getAllByText('Verifier').length).toBeGreaterThan(0);
  });

  it('navigates to the builder with the recipe prefilled when Edit pipeline is clicked', async () => {
    (collectionsApi.list as ReturnType<typeof vi.fn>).mockResolvedValue([collection]);
    (collectionsApi.listCommunity as ReturnType<typeof vi.fn>).mockResolvedValue(emptyCommunity);
    (collectionsApi.getArtifacts as ReturnType<typeof vi.fn>).mockResolvedValue([
      makeAgent({
        name: 'orchestrator',
        tags: ['mode:primary'],
        handoff_to: ['builder'],
        description: 'Routes work through the pipeline.',
      }),
      makeAgent({ name: 'builder', tags: ['mode:subagent'] }),
    ]);

    const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    render(
      <QueryClientProvider client={queryClient}>
        <ThemeProvider>
          <MemoryRouter initialEntries={['/build/orchestration']}>
            <Routes>
              <Route path="/build/orchestration" element={<OrchestrationGallery />} />
              <Route
                path="/build/orchestration/build"
                element={
                  <div>
                    builder-page
                    <EditStateProbe />
                  </div>
                }
              />
            </Routes>
          </MemoryRouter>
        </ThemeProvider>
      </QueryClientProvider>
    );

    fireEvent.click(await screen.findByText('Orchestrator'));
    fireEvent.click(await screen.findByRole('button', { name: /edit pipeline/i }));

    expect(await screen.findByText('builder-page')).toBeInTheDocument();
    expect(screen.getByTestId('edit-state').textContent).toBe('orchestrator');
  });

  it('marks a dangling handoff_to target as not found instead of dropping it', async () => {
    (collectionsApi.list as ReturnType<typeof vi.fn>).mockResolvedValue([collection]);
    (collectionsApi.listCommunity as ReturnType<typeof vi.fn>).mockResolvedValue(emptyCommunity);
    (collectionsApi.getArtifacts as ReturnType<typeof vi.fn>).mockResolvedValue([
      makeAgent({
        name: 'orchestrator',
        tags: ['mode:primary'],
        handoff_to: ['ghost-agent'],
      }),
    ]);

    renderPage();

    fireEvent.click(await screen.findByText('Orchestrator'));

    expect(await screen.findByText('Ghost Agent')).toBeInTheDocument();
    expect(screen.getByText('not found')).toBeInTheDocument();
  });
});
