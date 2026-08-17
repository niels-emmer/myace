import { render, screen, fireEvent } from '@testing-library/react';
import { MemoryRouter, Routes, Route } from 'react-router-dom';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import Layout from './Layout';
import { AuthProvider } from '../contexts/AuthContext';
import { authApi } from '../lib/api';
import type { User } from '../types';

vi.mock('../lib/api', () => ({
  authApi: { me: vi.fn() },
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
  return render(
    <MemoryRouter initialEntries={[path]}>
      <AuthProvider>
        <Routes>
          <Route element={<Layout />}>
            <Route path="*" element={<div>page-content</div>} />
          </Route>
        </Routes>
      </AuthProvider>
    </MemoryRouter>
  );
}

describe('Layout sidebar groups', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    (authApi.me as ReturnType<typeof vi.fn>).mockResolvedValue(mockUser);
  });

  it('collapses every group by default when on an unrelated route', async () => {
    renderAt('/');
    await screen.findByText('page-content');

    expect(screen.queryByRole('link', { name: /My Collections/ })).not.toBeInTheDocument();
    expect(screen.queryByRole('link', { name: /Profiles/ })).not.toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Expand Collections/ })).toBeInTheDocument();
  });

  it('auto-expands the group containing the active route', async () => {
    renderAt('/build/profiles');
    await screen.findByText('page-content');

    expect(screen.getByRole('link', { name: /^Profiles$/ })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Collapse Build/ })).toBeInTheDocument();
    // An unrelated group stays collapsed.
    expect(screen.queryByRole('link', { name: /My Collections/ })).not.toBeInTheDocument();
  });

  it('expands and collapses a group on chevron click', async () => {
    renderAt('/');
    await screen.findByText('page-content');

    fireEvent.click(screen.getByRole('button', { name: /Expand Collections/ }));
    expect(screen.getByRole('link', { name: /My Collections/ })).toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: /Collapse Collections/ }));
    expect(screen.queryByRole('link', { name: /My Collections/ })).not.toBeInTheDocument();
  });
});
