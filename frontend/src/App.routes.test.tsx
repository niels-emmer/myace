import { render, screen } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter } from 'react-router-dom';
import { describe, it, expect, beforeEach, vi } from 'vitest';
import App from './App';
import { AuthProvider } from './contexts/AuthContext';
import { ThemeProvider } from './contexts/ThemeContext';
import { authApi } from './lib/api';
import type { User } from './types';

vi.mock('./lib/api', () => ({
  authApi: { me: vi.fn() },
}));

// Stub every leaf page so this file only exercises App.tsx's route table
// (which path lands where), not each page's own data fetching.
vi.mock('./pages/Home', () => ({ default: () => <div>home-page</div> }));
vi.mock('./pages/ProfileComposer', () => ({ default: () => <div>setups-page</div> }));
vi.mock('./pages/ProfileDetail', async () => {
  const { useParams } = await import('react-router-dom');
  function SetupDetailStub() {
    const { id } = useParams();
    return <div>setup-detail:{id}</div>;
  }
  return { default: SetupDetailStub };
});
vi.mock('./pages/TargetExporter', async () => {
  const { useParams, useSearchParams } = await import('react-router-dom');
  function InstallStub() {
    const { id } = useParams();
    const [params] = useSearchParams();
    return <div>install-page:{id ?? ''}:{params.get('profile') ?? ''}</div>;
  }
  return { default: InstallStub };
});
vi.mock('./pages/PacksLibrary', () => ({ default: () => <div>packs-page</div> }));
vi.mock('./pages/CollectionsManager', () => ({ default: () => <div>my-packs-page</div> }));
vi.mock('./pages/OrchestrationGallery', () => ({ default: () => <div>pipelines-page</div> }));
vi.mock('./pages/OrchestratorBuilder', () => ({ default: () => <div>pipeline-new-page</div> }));
vi.mock('./pages/ImportPage', async () => {
  const { useSearchParams } = await import('react-router-dom');
  function ImportStub() {
    const [params] = useSearchParams();
    return <div>import-page:{params.get('source') ?? ''}</div>;
  }
  return { default: ImportStub };
});
vi.mock('./pages/PackDetail', async () => {
  const { useParams } = await import('react-router-dom');
  function PackDetailStub() {
    const { id } = useParams();
    return <div>pack-detail:{id}</div>;
  }
  return { default: PackDetailStub };
});
vi.mock('./pages/PublishPack', async () => {
  const { useParams } = await import('react-router-dom');
  function PublishStub() {
    const { id } = useParams();
    return <div>publish-page:{id}</div>;
  }
  return { default: PublishStub };
});
vi.mock('./pages/CollectionDetail', async () => {
  const { useParams } = await import('react-router-dom');
  function ManagePackStub() {
    const { id } = useParams();
    return <div>manage-pack:{id}</div>;
  }
  return { default: ManagePackStub };
});
vi.mock('./pages/NewArtifactRule', async () => {
  const { useParams } = await import('react-router-dom');
  function NewItemStub() {
    const { id } = useParams();
    return <div>new-item:{id}</div>;
  }
  return { default: NewItemStub };
});
vi.mock('./pages/MachinePage', async () => {
  const { useSearchParams } = await import('react-router-dom');
  function MachineStub() {
    const [params] = useSearchParams();
    return <div>machine-page:{params.get('tab') ?? 'overview'}</div>;
  }
  return { default: MachineStub };
});
vi.mock('./pages/SettingsHub', () => ({ default: () => <div>settings-page</div> }));
vi.mock('./pages/UserSettings', () => ({ default: () => <div>account-page</div> }));
vi.mock('./pages/ModerationQueue', () => ({ default: () => <div>moderation-page</div> }));
vi.mock('./pages/SystemSettings', () => ({ default: () => <div>system-page</div> }));

// Admin so the moderation/system redirect cases reach their destination
// instead of bouncing to "/" — role gating is covered separately.
const mockUser: User = {
  id: 'user-1',
  email: 'user@test.com',
  display_name: 'Test User',
  is_active: true,
  is_admin: true,
  role: 'admin',
  created_at: '2026-01-01T00:00:00Z',
};

function renderAt(path: string) {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <ThemeProvider>
      <QueryClientProvider client={queryClient}>
        <MemoryRouter initialEntries={[path]}>
          <AuthProvider>
            <App />
          </AuthProvider>
        </MemoryRouter>
      </QueryClientProvider>
    </ThemeProvider>
  );
}

describe('canonical routes', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    (authApi.me as ReturnType<typeof vi.fn>).mockResolvedValue(mockUser);
  });

  it.each([
    ['/', 'home-page'],
    ['/setups', 'setups-page'],
    ['/setups/abc', 'setup-detail:abc'],
    ['/setups/abc/install', 'install-page:abc:'],
    ['/packs', 'packs-page'],
    ['/packs/mine', 'my-packs-page'],
    ['/packs/pipelines', 'pipelines-page'],
    ['/packs/pipelines/new', 'pipeline-new-page'],
    ['/packs/import', 'import-page:'],
    ['/packs/abc', 'pack-detail:abc'],
    ['/packs/abc/publish', 'publish-page:abc'],
    ['/packs/abc/manage', 'manage-pack:abc'],
    ['/packs/abc/items/new', 'new-item:abc'],
    ['/machine', 'machine-page:overview'],
    ['/machine?tab=audit', 'machine-page:audit'],
    ['/machine?tab=sync', 'machine-page:sync'],
    ['/settings', 'settings-page'],
    ['/settings/account', 'account-page'],
    ['/settings/moderation', 'moderation-page'],
    ['/settings/system', 'system-page'],
  ])('%s renders its page', async (path, expectedText) => {
    renderAt(path);
    expect(await screen.findByText(expectedText)).toBeInTheDocument();
  });
});

describe('public browse routes', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    (authApi.me as ReturnType<typeof vi.fn>).mockRejectedValue(new Error('not authenticated'));
  });

  it.each([
    ['/packs', 'packs-page'],
    ['/packs/abc', 'pack-detail:abc'],
  ])('%s renders without a session', async (path, expectedText) => {
    renderAt(path);
    expect(await screen.findByText(expectedText)).toBeInTheDocument();
  });

  it('still protects the authenticated packs children', async () => {
    renderAt('/packs/mine');
    // PublicLayout is not rendered for an authenticated-only path; the
    // RequireAuth redirect sends the visitor to /welcome instead.
    expect(await screen.findByText(/Write your AI agent rules once/i)).toBeInTheDocument();
  });
});

describe('legacy route redirects', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    (authApi.me as ReturnType<typeof vi.fn>).mockResolvedValue(mockUser);
  });

  it.each([
    ['/collections', 'packs-page'],
    ['/collections/community', 'packs-page'],
    ['/collections/community/abc', 'pack-detail:abc'],
    // The old split community detail path merged into /packs/:id (decision A).
    ['/packs/community/abc', 'pack-detail:abc'],
    ['/collections/mine', 'my-packs-page'],
    ['/collections/abc', 'pack-detail:abc'],
    ['/collections/abc/artifacts/new', 'new-item:abc'],
    ['/build', 'setups-page'],
    ['/build/profiles', 'setups-page'],
    ['/build/profiles/abc', 'setup-detail:abc'],
    ['/build/compile', 'setups-page'],
    ['/build/orchestration', 'pipelines-page'],
    ['/build/orchestration/build', 'pipeline-new-page'],
    ['/profiles', 'setups-page'],
    ['/profiles/abc', 'setup-detail:abc'],
    ['/compile', 'setups-page'],
    ['/export', 'setups-page'],
    ['/orchestration', 'pipelines-page'],
    ['/orchestration/build', 'pipeline-new-page'],
    ['/import', 'import-page:'],
    ['/setup-audit', 'machine-page:audit'],
    ['/sync', 'machine-page:sync'],
    ['/machine/audit', 'machine-page:audit'],
    ['/machine/sync', 'machine-page:sync'],
    ['/machine/import', 'import-page:'],
    ['/moderation', 'moderation-page'],
    ['/admin/system', 'system-page'],
    // Query-preserving legacy redirects (old bookmarks preselected these).
    ['/compile?profile=abc', 'install-page:abc:'],
    ['/build/compile?profile=abc', 'install-page:abc:'],
    ['/import?source=git', 'import-page:git'],
    ['/machine/import?source=local', 'import-page:local'],
  ])('%s redirects to its canonical page', async (path, expectedText) => {
    renderAt(path);
    expect(await screen.findByText(expectedText)).toBeInTheDocument();
  });
});
