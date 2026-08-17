import { render, screen } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter } from 'react-router-dom';
import { describe, it, expect, beforeEach, vi } from 'vitest';
import App from './App';
import { AuthProvider } from './contexts/AuthContext';
import { authApi } from './lib/api';
import type { User } from './types';

vi.mock('./lib/api', () => ({
  authApi: { me: vi.fn() },
}));

// Stub the leaf pages that legacy redirects land on, so this test only
// exercises App.tsx's route table (which path redirects where), not each
// page's own data fetching.
vi.mock('./pages/ProfileComposer', () => ({ default: () => <div>profiles-page</div> }));
vi.mock('./pages/ProfileDetail', async () => {
  const { useParams } = await import('react-router-dom');
  function ProfileDetailStub() {
    const { id } = useParams();
    return <div>profile-detail-page:{id}</div>;
  }
  return { default: ProfileDetailStub };
});
vi.mock('./pages/OrchestrationGallery', () => ({ default: () => <div>orchestration-page</div> }));
vi.mock('./pages/OrchestratorBuilder', () => ({ default: () => <div>orchestration-build-page</div> }));
vi.mock('./pages/TargetExporter', () => ({ default: () => <div>compile-page</div> }));
vi.mock('./pages/ImportPage', () => ({ default: () => <div>import-page</div> }));
vi.mock('./pages/SetupAudit', () => ({ default: () => <div>setup-audit-page</div> }));
vi.mock('./pages/SyncDashboard', () => ({ default: () => <div>sync-page</div> }));

const mockUser: User = {
  id: 'user-1',
  email: 'user@test.com',
  display_name: 'Test User',
  is_active: true,
  is_admin: false,
  role: 'user',
  created_at: '2026-01-01T00:00:00Z',
};

function renderAt(path: string) {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={[path]}>
        <AuthProvider>
          <App />
        </AuthProvider>
      </MemoryRouter>
    </QueryClientProvider>
  );
}

describe('legacy top-level route redirects', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    (authApi.me as ReturnType<typeof vi.fn>).mockResolvedValue(mockUser);
  });

  it.each([
    ['/profiles', 'profiles-page'],
    ['/orchestration', 'orchestration-page'],
    ['/orchestration/build', 'orchestration-build-page'],
    ['/compile', 'compile-page'],
    ['/export', 'compile-page'],
    ['/import', 'import-page'],
    ['/setup-audit', 'setup-audit-page'],
    ['/sync', 'sync-page'],
  ])('redirects %s to the grouped route', async (path, expectedText) => {
    renderAt(path);
    expect(await screen.findByText(expectedText)).toBeInTheDocument();
  });

  it('redirects /profiles/:id to /build/profiles/:id, preserving the id param', async () => {
    renderAt('/profiles/abc-123');
    expect(await screen.findByText('profile-detail-page:abc-123')).toBeInTheDocument();
  });
});
