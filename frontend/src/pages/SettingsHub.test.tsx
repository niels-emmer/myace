import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import SettingsHub from './SettingsHub';
import { AuthProvider } from '../contexts/AuthContext';
import { authApi } from '../lib/api';
import type { User } from '../types';

vi.mock('../lib/api', () => ({
  authApi: { me: vi.fn() },
}));

function makeUser(overrides: Partial<User> = {}): User {
  return {
    id: 'user-1',
    email: 'user@test.com',
    display_name: 'Test User',
    is_active: true,
    is_admin: false,
    role: 'user',
    created_at: '2026-01-01T00:00:00Z',
    ...overrides,
  };
}

function renderPage() {
  return render(
    <MemoryRouter>
      <AuthProvider>
        <SettingsHub />
      </AuthProvider>
    </MemoryRouter>
  );
}

describe('SettingsHub', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('shows only Account for a regular user', async () => {
    (authApi.me as ReturnType<typeof vi.fn>).mockResolvedValue(makeUser());
    renderPage();

    expect(await screen.findByRole('link', { name: /Account/ })).toHaveAttribute(
      'href',
      '/settings/account'
    );
    expect(screen.queryByRole('link', { name: /Moderation/ })).not.toBeInTheDocument();
    expect(screen.queryByRole('link', { name: /System/ })).not.toBeInTheDocument();
  });

  it('adds Moderation for a moderator', async () => {
    (authApi.me as ReturnType<typeof vi.fn>).mockResolvedValue(makeUser({ role: 'moderator' }));
    renderPage();

    expect(await screen.findByRole('link', { name: /Moderation/ })).toHaveAttribute(
      'href',
      '/settings/moderation'
    );
    expect(screen.queryByRole('link', { name: /System/ })).not.toBeInTheDocument();
  });

  it('adds Moderation and System for an admin', async () => {
    (authApi.me as ReturnType<typeof vi.fn>).mockResolvedValue(
      makeUser({ role: 'admin', is_admin: true })
    );
    renderPage();

    expect(await screen.findByRole('link', { name: /Moderation/ })).toHaveAttribute(
      'href',
      '/settings/moderation'
    );
    expect(screen.getByRole('link', { name: /System/ })).toHaveAttribute(
      'href',
      '/settings/system'
    );
  });
});
