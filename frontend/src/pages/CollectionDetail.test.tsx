import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter } from 'react-router-dom';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import CollectionDetail from './CollectionDetail';

// Mock react-router-dom
const mockNavigate = vi.fn();
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom');
  return {
    ...actual,
    useParams: () => ({ id: 'test-collection-id' }),
    useNavigate: () => mockNavigate,
  };
});

// Mock the API module
vi.mock('../lib/api', () => ({
  collectionsApi: {
    get: vi.fn(),
    getArtifacts: vi.fn(),
    list: vi.fn(),
    update: vi.fn(),
    delete: vi.fn(),
    bulkDeleteArtifacts: vi.fn(),
    bulkExportArtifacts: vi.fn(),
    exportToGithub: vi.fn(),
    updateArtifact: vi.fn(),
  },
}));

import { collectionsApi } from '../lib/api';

const mockCollection = {
  id: 'test-collection-id',
  owner_id: 'user-1',
  name: 'Test Collection',
  description: 'A test collection',
  git_url: 'https://github.com/test/test.git',
  git_branch: 'main',
  collection_type: 'base',
  visibility: 'private',
  is_active: true,
  artifact_count: 3,
  last_synced_at: null,
  created_at: '2025-01-01T00:00:00Z',
  updated_at: '2025-01-01T00:00:00Z',
};

const mockArtifacts = [
  {
    id: 'art-1',
    collection_id: 'test-collection-id',
    artifact_type: 'rule',
    name: 'Test Rule',
    version: '1.0.0',
    priority: 50,
    target_compatibility: [],
    tags: [],
    description: 'A test rule',
    body: 'rule content',
    file_path: 'rules/test.md',
    is_enabled: true,
    created_at: '2025-01-01T00:00:00Z',
    updated_at: '2025-01-01T00:00:00Z',
  },
];

const mockMixedArtifacts = [
  { ...mockArtifacts[0], id: 'art-rule-1', artifact_type: 'rule', name: 'Rule One' },
  { ...mockArtifacts[0], id: 'art-skill-1', artifact_type: 'skill', name: 'Skill One' },
  { ...mockArtifacts[0], id: 'art-skill-2', artifact_type: 'skill', name: 'Skill Two' },
  { ...mockArtifacts[0], id: 'art-agent-1', artifact_type: 'agent', name: 'Agent One' },
];

function renderCollectionDetail() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>
        <CollectionDetail />
      </MemoryRouter>
    </QueryClientProvider>
  );
}

describe('CollectionDetail — action buttons', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    (collectionsApi.get as ReturnType<typeof vi.fn>).mockResolvedValue(mockCollection);
    (collectionsApi.getArtifacts as ReturnType<typeof vi.fn>).mockResolvedValue(mockArtifacts);
    (collectionsApi.list as ReturnType<typeof vi.fn>).mockResolvedValue([]);
  });

  describe('Delete button', () => {
    it('renders a Delete button next to Edit', async () => {
      renderCollectionDetail();

      const deleteBtn = await screen.findByRole('button', { name: /Delete/i });
      expect(deleteBtn).toBeInTheDocument();
    });

    it('shows a confirmation modal when Delete is clicked', async () => {
      renderCollectionDetail();

      const deleteBtn = await screen.findByRole('button', { name: /Delete/i });
      fireEvent.click(deleteBtn);

      // The modal title uses &ldquo;/&rdquo; HTML entities for smart quotes
      expect(
        screen.getByText(/Delete.*Test Collection.*\?/)
      ).toBeInTheDocument();
      expect(
        screen.getByText(/permanently disable this collection/)
      ).toBeInTheDocument();
    });

    it('calls delete API and navigates to /collections on confirm', async () => {
      (collectionsApi.delete as ReturnType<typeof vi.fn>).mockResolvedValue(undefined);
      renderCollectionDetail();

      const deleteBtn = await screen.findByRole('button', { name: /Delete/i });
      fireEvent.click(deleteBtn);

      // There are two "Delete" buttons: the header button and the modal confirm button
      const confirmBtns = screen.getAllByRole('button', { name: /^Delete$/ });
      const confirmBtn = confirmBtns[1]; // The second one is in the modal
      fireEvent.click(confirmBtn);

      await waitFor(() => {
        expect(collectionsApi.delete).toHaveBeenCalledWith('test-collection-id');
      });
      await waitFor(() => {
        expect(mockNavigate).toHaveBeenCalledWith('/collections');
      });
    });

    it('closes the modal when Cancel is clicked', async () => {
      renderCollectionDetail();

      const deleteBtn = await screen.findByRole('button', { name: /Delete/i });
      fireEvent.click(deleteBtn);

      const cancelBtn = screen.getByRole('button', { name: /Cancel/i });
      fireEvent.click(cancelBtn);

      expect(
        screen.queryByText(/Delete.*Test Collection.*\?/)
      ).not.toBeInTheDocument();
    });

    it('shows an error message when delete fails', async () => {
      (collectionsApi.delete as ReturnType<typeof vi.fn>).mockRejectedValue(
        new Error('Server error')
      );
      renderCollectionDetail();

      const deleteBtn = await screen.findByRole('button', { name: /Delete/i });
      fireEvent.click(deleteBtn);

      const confirmBtns = screen.getAllByRole('button', { name: /^Delete$/ });
      const confirmBtn = confirmBtns[1]; // The second one is in the modal
      fireEvent.click(confirmBtn);

      expect(await screen.findByText('Server error')).toBeInTheDocument();
    });
  });

  describe('Share button', () => {
    it('renders a Share button next to Edit', async () => {
      renderCollectionDetail();

      const shareBtn = await screen.findByRole('button', { name: /Share/i });
      expect(shareBtn).toBeInTheDocument();
    });

    it('shows a modal with Private/Public toggle when Share is clicked', async () => {
      renderCollectionDetail();

      const shareBtn = await screen.findByRole('button', { name: /Share/i });
      fireEvent.click(shareBtn);

      expect(screen.getByText('Share Collection')).toBeInTheDocument();
      expect(screen.getByText('Private')).toBeInTheDocument();
      expect(screen.getByText('Public')).toBeInTheDocument();
    });

    it('defaults to the current visibility in the share modal', async () => {
      renderCollectionDetail();

      const shareBtn = await screen.findByRole('button', { name: /Share/i });
      fireEvent.click(shareBtn);

      // Current visibility is 'private', so Private button should be active
      const privateBtn = screen.getByText('Private').closest('button');
      expect(privateBtn?.className).toContain('border-brand-500');
    });

    it('calls update API with new visibility on save', async () => {
      (collectionsApi.update as ReturnType<typeof vi.fn>).mockResolvedValue({
        ...mockCollection,
        visibility: 'public',
      });
      renderCollectionDetail();

      const shareBtn = await screen.findByRole('button', { name: /Share/i });
      fireEvent.click(shareBtn);

      // Switch to public
      const publicBtn = screen.getByText('Public').closest('button')!;
      fireEvent.click(publicBtn);

      // Click Save
      const saveBtn = screen.getByRole('button', { name: /Save/i });
      fireEvent.click(saveBtn);

      await waitFor(() => {
        expect(collectionsApi.update).toHaveBeenCalledWith('test-collection-id', {
          visibility: 'public',
        });
      });
    });

    it('disables Save when visibility has not changed', async () => {
      renderCollectionDetail();

      const shareBtn = await screen.findByRole('button', { name: /Share/i });
      fireEvent.click(shareBtn);

      const saveBtn = screen.getByRole('button', { name: /Save/i });
      expect(saveBtn).toBeDisabled();
    });

    it('closes the share modal on Cancel', async () => {
      renderCollectionDetail();

      const shareBtn = await screen.findByRole('button', { name: /Share/i });
      fireEvent.click(shareBtn);

      const cancelBtn = screen.getAllByText('Cancel')[0];
      fireEvent.click(cancelBtn);

      expect(screen.queryByText('Share Collection')).not.toBeInTheDocument();
    });
  });

  describe('Publish to Community button', () => {
    it('renders a Publish to Community button', async () => {
      renderCollectionDetail();

      const publishBtn = await screen.findByRole('button', { name: /Publish to Community/i });
      expect(publishBtn).toBeInTheDocument();
      expect(publishBtn).not.toBeDisabled();
    });

    it('has a tooltip indicating the publish action', async () => {
      renderCollectionDetail();

      const publishBtn = await screen.findByRole('button', { name: /Publish to Community/i });
      expect(publishBtn).toHaveAttribute('title', 'Publish to community collections');
    });
  });

  describe('Button visibility during editing', () => {
    it('hides action buttons when editing is active', async () => {
      renderCollectionDetail();

      const editBtn = await screen.findByRole('button', { name: /Edit/i });
      fireEvent.click(editBtn);

      // Action buttons should be hidden during editing
      expect(screen.queryByRole('button', { name: /Delete/i })).not.toBeInTheDocument();
      expect(screen.queryByRole('button', { name: /Share/i })).not.toBeInTheDocument();
      expect(screen.queryByRole('button', { name: /Publish to Community/i })).not.toBeInTheDocument();
    });
  });

  describe('Category counts', () => {
    // Regression test for #51: the artifact list must be fetched once,
    // unfiltered, and counted client-side — refetching per-type would make
    // every non-active category show (0) after selecting a filter.
    it('keeps every category count correct after selecting a filter, and after returning to All', async () => {
      (collectionsApi.getArtifacts as ReturnType<typeof vi.fn>).mockResolvedValue(
        mockMixedArtifacts
      );
      renderCollectionDetail();

      const allBtn = await screen.findByRole('button', { name: /All\(4\)/ });
      const rulesBtn = screen.getByRole('button', { name: /Rules\(1\)/ });
      const skillsBtn = screen.getByRole('button', { name: /Skills\(2\)/ });
      const agentsBtn = screen.getByRole('button', { name: /Agents\(1\)/ });
      expect(allBtn).toBeInTheDocument();

      fireEvent.click(skillsBtn);

      expect(screen.getByRole('button', { name: /All\(4\)/ })).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /Rules\(1\)/ })).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /Skills\(2\)/ })).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /Agents\(1\)/ })).toBeInTheDocument();

      fireEvent.click(rulesBtn);

      expect(screen.getByRole('button', { name: /All\(4\)/ })).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /Rules\(1\)/ })).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /Skills\(2\)/ })).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /Agents\(1\)/ })).toBeInTheDocument();

      fireEvent.click(agentsBtn);

      expect(screen.getByRole('button', { name: /All\(4\)/ })).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /Rules\(1\)/ })).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /Skills\(2\)/ })).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /Agents\(1\)/ })).toBeInTheDocument();

      // Only a single API fetch should ever happen — counts come from
      // client-side filtering, not per-tab refetches.
      expect(collectionsApi.getArtifacts).toHaveBeenCalledTimes(1);
    });
  });
});
