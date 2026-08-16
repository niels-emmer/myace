import { render, screen, fireEvent } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter } from 'react-router-dom';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import CommunityCollectionDetail from './CommunityCollectionDetail';
import { AuthProvider } from '../contexts/AuthContext';

vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom');
  return {
    ...actual,
    useParams: () => ({ id: 'test-collection-id' }),
    useNavigate: () => vi.fn(),
  };
});

vi.mock('../lib/api', () => ({
  collectionsApi: {
    get: vi.fn(),
    getArtifacts: vi.fn(),
    importCommunity: vi.fn(),
    verify: vi.fn(),
  },
  authApi: {
    me: vi.fn().mockRejectedValue(new Error('not logged in')),
  },
  moderationApi: {
    updateMeta: vi.fn(),
  },
  ratingsApi: {
    get: vi.fn().mockResolvedValue({ avg_rating: 0, rating_count: 0, my_rating: null }),
    rate: vi.fn(),
    remove: vi.fn(),
  },
  commentsApi: {
    list: vi.fn().mockResolvedValue([]),
    create: vi.fn(),
    remove: vi.fn(),
  },
}));

import { collectionsApi } from '../lib/api';

const mockCollection = {
  id: 'test-collection-id',
  owner_id: 'user-1',
  name: 'Community Collection',
  description: 'A community collection',
  git_url: null,
  git_branch: 'main',
  collection_type: 'base',
  visibility: 'public',
  is_active: true,
  published: true,
  download_count: 7,
  artifact_count: 4,
  last_synced_at: null,
  created_at: '2025-01-01T00:00:00Z',
  updated_at: '2025-01-01T00:00:00Z',
};

const baseArtifact = {
  collection_id: 'test-collection-id',
  version: '1.0.0',
  priority: 50,
  target_compatibility: [],
  tags: [],
  description: 'desc',
  body: 'content',
  file_path: 'x.md',
  is_enabled: true,
  created_at: '2025-01-01T00:00:00Z',
  updated_at: '2025-01-01T00:00:00Z',
};

const mockMixedArtifacts = [
  { ...baseArtifact, id: 'art-rule-1', artifact_type: 'rule', name: 'Rule One' },
  { ...baseArtifact, id: 'art-skill-1', artifact_type: 'skill', name: 'Skill One' },
  { ...baseArtifact, id: 'art-skill-2', artifact_type: 'skill', name: 'Skill Two' },
  { ...baseArtifact, id: 'art-agent-1', artifact_type: 'agent', name: 'Agent One' },
];

function renderPage() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>
        <AuthProvider>
          <CommunityCollectionDetail />
        </AuthProvider>
      </MemoryRouter>
    </QueryClientProvider>
  );
}

describe('CommunityCollectionDetail — category counts', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    (collectionsApi.get as ReturnType<typeof vi.fn>).mockResolvedValue(mockCollection);
    (collectionsApi.getArtifacts as ReturnType<typeof vi.fn>).mockResolvedValue(
      mockMixedArtifacts
    );
  });

  // Regression test: this page had the same bug PR #51 fixed on the owned-
  // collection page — artifacts were refetched from the server filtered by
  // type, so counts derived from that list showed (0) for every category
  // except the selected one.
  it('keeps every category count correct after selecting each filter', async () => {
    renderPage();

    const allBtn = await screen.findByRole('button', { name: /All\(4\)/ });
    expect(allBtn).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Rules\(1\)/ })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Skills\(2\)/ })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Agents\(1\)/ })).toBeInTheDocument();

    for (const label of [/Skills\(2\)/, /Rules\(1\)/, /Agents\(1\)/]) {
      fireEvent.click(screen.getByRole('button', { name: label }));

      expect(screen.getByRole('button', { name: /All\(4\)/ })).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /Rules\(1\)/ })).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /Skills\(2\)/ })).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /Agents\(1\)/ })).toBeInTheDocument();
    }

    // A single unfiltered fetch — counts come from client-side filtering.
    expect(collectionsApi.getArtifacts).toHaveBeenCalledTimes(1);
    expect(collectionsApi.getArtifacts).toHaveBeenCalledWith('test-collection-id', {
      include_disabled: true,
    });
  });

  it('shows a "not yet verified" badge and no verify button for a non-moderator', async () => {
    renderPage();

    expect(await screen.findByText('Not yet verified')).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /Mark verified/i })).not.toBeInTheDocument();
  });

  it('shows only the selected type in the artifact list', async () => {
    renderPage();

    expect(await screen.findByText('Rule One')).toBeInTheDocument();
    expect(screen.getByText('Skill One')).toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: /Skills\(2\)/ }));

    expect(screen.getByText('Skill One')).toBeInTheDocument();
    expect(screen.getByText('Skill Two')).toBeInTheDocument();
    expect(screen.queryByText('Rule One')).not.toBeInTheDocument();
    expect(screen.queryByText('Agent One')).not.toBeInTheDocument();
  });
});
