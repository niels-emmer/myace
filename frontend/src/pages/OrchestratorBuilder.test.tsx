import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter } from 'react-router-dom';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import OrchestratorBuilder from './OrchestratorBuilder';
import { AuthProvider } from '../contexts/AuthContext';
import { ThemeProvider } from '../contexts/ThemeContext';
import { collectionsApi, profilesApi, authApi } from '../lib/api';
import type { Profile, Collection, Artifact, User } from '../types';

vi.mock('../lib/api', () => ({
  collectionsApi: {
    list: vi.fn(),
    getArtifacts: vi.fn(),
    createArtifact: vi.fn(),
  },
  profilesApi: {
    list: vi.fn(),
  },
  authApi: {
    me: vi.fn(),
  },
}));

// @xyflow/react's <ReactFlow> preview measures its container via
// ResizeObserver, which jsdom doesn't implement.
class ResizeObserverStub {
  observe() {}
  unobserve() {}
  disconnect() {}
}
vi.stubGlobal('ResizeObserver', ResizeObserverStub);

const mockUser: User = {
  id: 'user-1',
  email: 'owner@test.com',
  display_name: 'Owner',
  is_active: true,
  is_admin: false,
  role: 'user',
  created_at: '2026-01-01T00:00:00Z',
};

const mockProfile: Profile = {
  id: 'profile-1',
  owner_id: 'user-1',
  name: 'my-profile',
  base_collection_id: 'collection-1',
  additional_collection_ids: [],
  disabled_artifact_ids: [],
  is_public: false,
  version: 1,
  created_at: '2026-01-01T00:00:00Z',
  updated_at: '2026-01-01T00:00:00Z',
};

const mockOwnedCollection: Collection = {
  id: 'own-collection-1',
  owner_id: 'user-1',
  name: 'my-collection',
  git_url: 'https://example.com/repo.git',
  git_branch: 'main',
  collection_type: 'base',
  visibility: 'private',
  is_active: true,
  artifact_count: 0,
  download_count: 0,
  published: false,
  avg_rating: 0,
  rating_count: 0,
  moderation_status: 'draft',
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
    tags: ['mode:subagent'],
    description: '',
    body: '',
    file_path: 'agents/agent.md',
    is_enabled: true,
    created_at: '2026-01-01T00:00:00Z',
    updated_at: '2026-01-01T00:00:00Z',
    ...overrides,
  };
}

function renderPage(initialEntries?: Parameters<typeof MemoryRouter>[0]['initialEntries']) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <ThemeProvider>
        <MemoryRouter initialEntries={initialEntries}>
          <AuthProvider>
            <OrchestratorBuilder />
          </AuthProvider>
        </MemoryRouter>
      </ThemeProvider>
    </QueryClientProvider>
  );
}

describe('OrchestratorBuilder', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    (authApi.me as ReturnType<typeof vi.fn>).mockResolvedValue(mockUser);
    (profilesApi.list as ReturnType<typeof vi.fn>).mockResolvedValue([mockProfile]);
    (collectionsApi.list as ReturnType<typeof vi.fn>).mockResolvedValue([mockOwnedCollection]);
    (collectionsApi.getArtifacts as ReturnType<typeof vi.fn>).mockResolvedValue([
      makeAgent({ name: 'builder', description: 'Implements changes.' }),
      makeAgent({ name: 'verifier', description: 'Runs tests.' }),
    ]);
  });

  it('shows the non-goal callout for conditional branching', async () => {
    renderPage();
    expect(
      await screen.findByText(/only builds a straight-line pipeline/i)
    ).toBeInTheDocument();
  });

  it('lists available agents once a profile is selected, and adds them to the sequence', async () => {
    renderPage();

    fireEvent.change(await screen.findByDisplayValue('Select a profile...'), {
      target: { value: 'profile-1' },
    });

    expect(await screen.findByText('Builder')).toBeInTheDocument();
    expect(screen.getByText('Verifier')).toBeInTheDocument();

    const addButtons = screen.getAllByText('Add');
    fireEvent.click(addButtons[0]);

    expect(await screen.findByText('Pipeline sequence')).toBeInTheDocument();
    // The sequence panel now shows the added agent with its position number.
    expect(screen.getAllByText('Builder').length).toBeGreaterThan(1);
  });

  it('saves the generated artifact into the chosen collection', async () => {
    (collectionsApi.createArtifact as ReturnType<typeof vi.fn>).mockResolvedValue({
      ...makeAgent({ name: 'pipeline-orchestrator' }),
    });

    renderPage();

    fireEvent.change(await screen.findByDisplayValue('Select a profile...'), {
      target: { value: 'profile-1' },
    });
    fireEvent.click((await screen.findAllByText('Add'))[0]);

    fireEvent.change(await screen.findByDisplayValue('Select one of your collections...'), {
      target: { value: 'own-collection-1' },
    });

    fireEvent.click(screen.getByRole('button', { name: /generate & save/i }));

    await waitFor(() => {
      expect(collectionsApi.createArtifact).toHaveBeenCalledWith(
        'own-collection-1',
        expect.objectContaining({
          artifact_type: 'agent',
          name: 'pipeline-orchestrator',
          tags: ['mode:primary'],
          handoff_to: ['builder'],
        })
      );
    });

    expect(await screen.findByRole('link', { name: /orchestration gallery/i })).toBeInTheDocument();
  });

  it('prefills fields from an edit-recipe passed via router state', async () => {
    renderPage([
      {
        pathname: '/build/orchestration/build',
        state: {
          editRecipe: {
            collectionId: 'collection-1',
            collectionName: 'Software Engineer',
            primary: makeAgent({
              name: 'orchestrator',
              description: 'Routes work through specialists.',
              handoff_to: ['builder', 'verifier'],
            }),
          },
        },
      },
    ]);

    // Editing banner names the recipe and its source collection.
    expect(
      await screen.findByText(
        (_, el) => (el?.tagName === 'P' && el?.textContent?.includes('Editing orchestrator from Software Engineer')) ?? false
      )
    ).toBeInTheDocument();

    // Agent name input is prefilled from the recipe's primary agent.
    expect(await screen.findByDisplayValue('orchestrator')).toBeInTheDocument();

    // The handoff sequence is prefilled and rendered in the sequence panel.
    expect(await screen.findByText('Pipeline sequence')).toBeInTheDocument();
    expect(screen.getAllByText('Builder').length).toBeGreaterThan(0);
    expect(screen.getAllByText('Verifier').length).toBeGreaterThan(0);
  });

  it('blocks saving when the new agent name collides with a sequence member', async () => {
    renderPage();

    fireEvent.change(await screen.findByDisplayValue('Select a profile...'), {
      target: { value: 'profile-1' },
    });
    // Add "builder" to the sequence.
    fireEvent.click((await screen.findAllByText('Add'))[0]);

    const nameInput = await screen.findByDisplayValue('pipeline-orchestrator');
    fireEvent.change(nameInput, { target: { value: 'builder' } });

    expect(
      await screen.findByText(/is already in the sequence below/i)
    ).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /generate & save/i })).toBeDisabled();

    fireEvent.click(screen.getByRole('button', { name: /generate & save/i }));
    expect(collectionsApi.createArtifact).not.toHaveBeenCalled();
  });
});
