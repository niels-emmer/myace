import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { useState } from 'react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { AuthProvider, useAuth, type LoginOutcome } from './AuthContext';
import { authApi } from '../lib/api';
import type { User } from '../types';

vi.mock('../lib/api', () => ({
  authApi: { me: vi.fn(), login: vi.fn(), loginMfa: vi.fn(), setupTotp: vi.fn(), verifyTotp: vi.fn() },
}));

const mockUser: User = {
  id: 'u1',
  email: 'u@test.com',
  display_name: 'U',
  is_active: true,
  is_admin: false,
  role: 'user',
  created_at: '2026-01-01T00:00:00Z',
};

const me = () => authApi.me as ReturnType<typeof vi.fn>;
const loginApi = () => authApi.login as ReturnType<typeof vi.fn>;

function Harness() {
  const { user, login, completeMfaLogin } = useAuth();
  const [outcome, setOutcome] = useState<LoginOutcome | null>(null);
  return (
    <div>
      <span data-testid="user">{user ? user.email : 'none'}</span>
      <span data-testid="outcome">{outcome ? outcome.status : 'none'}</span>
      <button
        onClick={() => {
          void login('u@test.com', 'pw').then(setOutcome);
        }}
      >
        sign-in
      </button>
      <button
        onClick={() => {
          void completeMfaLogin('tok', '123456');
        }}
      >
        complete
      </button>
    </div>
  );
}

function renderHarness() {
  return render(
    <AuthProvider>
      <Harness />
    </AuthProvider>,
  );
}

describe('AuthProvider login', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    me().mockRejectedValue(new Error('401'));
  });

  it('authenticates when the API returns a real user', async () => {
    loginApi().mockResolvedValue(mockUser);
    renderHarness();
    fireEvent.click(screen.getByText('sign-in'));
    await waitFor(() => expect(screen.getByTestId('outcome')).toHaveTextContent('authenticated'));
    expect(screen.getByTestId('user')).toHaveTextContent('u@test.com');
  });

  it('does not establish an authenticated state for an MFA challenge', async () => {
    loginApi().mockResolvedValue({
      mfa_required: true,
      mfa_token: 'tok',
      message: 'MFA code required',
    });
    renderHarness();
    fireEvent.click(screen.getByText('sign-in'));
    await waitFor(() => expect(screen.getByTestId('outcome')).toHaveTextContent('mfa_required'));
    // The challenge object is not a session — the UI must stay unauthenticated.
    expect(screen.getByTestId('user')).toHaveTextContent('none');
  });

  it('sets the user only after the MFA step has issued a session', async () => {
    (authApi.loginMfa as ReturnType<typeof vi.fn>).mockResolvedValue({
      message: 'MFA verified',
      user_id: 'u1',
    });
    renderHarness();
    await waitFor(() => expect(me()).toHaveBeenCalled());
    me().mockResolvedValue(mockUser);

    fireEvent.click(screen.getByText('complete'));

    await waitFor(() => expect(screen.getByTestId('user')).toHaveTextContent('u@test.com'));
    expect(authApi.loginMfa).toHaveBeenCalledWith({ mfa_token: 'tok', code: '123456' });
    expect(me()).toHaveBeenCalled();
  });
});
