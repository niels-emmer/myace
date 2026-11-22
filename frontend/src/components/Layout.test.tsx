import { render, screen, fireEvent } from '@testing-library/react';
import { MemoryRouter, Routes, Route } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import Layout from './Layout';
import { AuthProvider } from '../contexts/AuthContext';
import { ThemeProvider } from '../contexts/ThemeContext';
import { authApi, collectionsApi, profilesApi } from '../lib/api';
import type { User } from '../types';

vi.mock('../lib/api', () => ({
  authApi: { me: vi.fn() },
  collectionsApi: { list: vi.fn() },
  profilesApi: { list: vi.fn() },
}));

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
    <ThemeProvider>
      <QueryClientProvider client={queryClient}>
        <MemoryRouter initialEntries={[path]}>
          <AuthProvider>
            <Routes>
              <Route element={<Layout />}>
                <Route path="*" element={<div>page-content</div>} />
              </Route>
            </Routes>
          </AuthProvider>
        </MemoryRouter>
      </QueryClientProvider>
    </ThemeProvider>
  );
}

describe('Layout sidebar', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    (authApi.me as ReturnType<typeof vi.fn>).mockResolvedValue(mockUser);
    (collectionsApi.list as ReturnType<typeof vi.fn>).mockResolvedValue([]);
    (profilesApi.list as ReturnType<typeof vi.fn>).mockResolvedValue([]);
  });

  it('shows single-link Home and Setups plus collapsed Packs and Settings groups', async () => {
    renderAt('/');
    await screen.findByText('page-content');

    expect(screen.getByRole('link', { name: /^Home$/ })).toHaveAttribute('href', '/');
    expect(screen.getByRole('link', { name: /^Setups$/ })).toHaveAttribute('href', '/setups');
    expect(screen.getByRole('button', { name: /Expand Packs/ })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Expand Settings/ })).toBeInTheDocument();
    expect(screen.queryByRole('link', { name: /My packs/ })).not.toBeInTheDocument();
    expect(screen.queryByRole('link', { name: /Account/ })).not.toBeInTheDocument();
  });

  it('auto-expands Packs when a pack route is active', async () => {
    renderAt('/packs/mine');
    await screen.findByText('page-content');

    expect(screen.getByRole('link', { name: /Browse packs/ })).toBeInTheDocument();
    expect(screen.getByRole('link', { name: /My packs/ })).toBeInTheDocument();
    expect(screen.getByRole('link', { name: /Pipelines/ })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Collapse Packs/ })).toBeInTheDocument();
    // An unrelated group stays collapsed.
    expect(screen.queryByRole('link', { name: /Account/ })).not.toBeInTheDocument();
  });

  it('expands and collapses a group on chevron click', async () => {
    renderAt('/');
    await screen.findByText('page-content');

    fireEvent.click(screen.getByRole('button', { name: /Expand Settings/ }));
    expect(screen.getByRole('link', { name: /Account/ })).toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: /Collapse Settings/ }));
    expect(screen.queryByRole('link', { name: /Account/ })).not.toBeInTheDocument();
  });

  it('renders My machine as a secondary footer link, not a nav group', async () => {
    renderAt('/');
    await screen.findByText('page-content');

    expect(screen.getByRole('link', { name: /My machine/ })).toHaveAttribute('href', '/machine');
    expect(screen.queryByRole('button', { name: /Expand My machine/ })).not.toBeInTheDocument();
  });

  it('shows the top-bar breadcrumb and opens the command palette from the search button', async () => {
    renderAt('/packs/mine');
    await screen.findByText('page-content');

    const breadcrumb = screen.getByRole('navigation', { name: /Breadcrumb/i });
    expect(breadcrumb).toHaveTextContent('Packs');
    expect(breadcrumb).toHaveTextContent('My packs');

    fireEvent.click(screen.getAllByRole('button', { name: /Search \(Command K\)/i })[0]);
    expect(await screen.findByRole('dialog', { name: /Command palette/i })).toBeInTheDocument();
  });

  it('opens the command palette with Ctrl+K', async () => {
    renderAt('/');
    await screen.findByText('page-content');

    fireEvent.keyDown(window, { key: 'k', ctrlKey: true });
    expect(await screen.findByRole('dialog', { name: /Command palette/i })).toBeInTheDocument();
  });
});
