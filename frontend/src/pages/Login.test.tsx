import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import Login from './Login';
import { AuthProvider } from '../contexts/AuthContext';
import { authApi } from '../lib/api';
import type { User } from '../types';

vi.mock('../lib/api', () => ({
  authApi: {
    me: vi.fn(),
    login: vi.fn(),
    loginMfa: vi.fn(),
    providers: vi.fn(),
    loginWithProvider: vi.fn(),
    setupTotp: vi.fn(),
    verifyTotp: vi.fn(),
  },
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

function renderLogin() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={['/login']}>
        <AuthProvider>
          <Login />
        </AuthProvider>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

async function submitCredentials() {
  fireEvent.change(screen.getByLabelText(/email/i), { target: { value: 'u@test.com' } });
  fireEvent.change(screen.getByLabelText(/password/i), { target: { value: 'pw' } });
  clickSubmit(/^log in$/i);
}

/** The "Log in" text appears on both the mode tab and the submit button. */
function clickSubmit(name: RegExp) {
  const submit = screen
    .getAllByRole('button', { name })
    .find((b) => b.getAttribute('type') === 'submit');
  if (!submit) throw new Error(`no submit button matching ${name}`);
  fireEvent.click(submit);
}

describe('Login — MFA challenge', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    me().mockRejectedValue(new Error('401'));
    (authApi.providers as ReturnType<typeof vi.fn>).mockResolvedValue({
      oidc: false,
      github: false,
      google: false,
    });
  });

  it('shows the code step instead of authenticating when MFA is required', async () => {
    loginApi().mockResolvedValue({
      mfa_required: true,
      mfa_token: 'tok',
      message: 'MFA code required',
    });
    renderLogin();
    await submitCredentials();

    expect(await screen.findByLabelText(/authentication code/i)).toBeInTheDocument();
    expect(authApi.loginMfa).not.toHaveBeenCalled();
    // The challenge response must not have been stored as a session.
    expect(screen.getByLabelText(/authentication code/i)).toBeInTheDocument();
  });

  it('completes the login by exchanging the challenge for a real session', async () => {
    loginApi().mockResolvedValue({
      mfa_required: true,
      mfa_token: 'tok',
      message: 'MFA code required',
    });
    (authApi.loginMfa as ReturnType<typeof vi.fn>).mockResolvedValue({
      message: 'MFA verified',
      user_id: 'u1',
    });
    renderLogin();
    await submitCredentials();

    const codeInput = await screen.findByLabelText(/authentication code/i);
    me().mockResolvedValue(mockUser);
    fireEvent.change(codeInput, { target: { value: '123456' } });
    clickSubmit(/^verify$/i);

    await waitFor(() =>
      expect(authApi.loginMfa).toHaveBeenCalledWith({ mfa_token: 'tok', code: '123456' }),
    );
    // The user is only loaded from the server once the session cookie exists.
    await waitFor(() => expect(me()).toHaveBeenCalled());
  });

  it('surfaces a rejected code without authenticating', async () => {
    loginApi().mockResolvedValue({
      mfa_required: true,
      mfa_token: 'tok',
      message: 'MFA code required',
    });
    (authApi.loginMfa as ReturnType<typeof vi.fn>).mockRejectedValue(
      new Error('Invalid verification code'),
    );
    renderLogin();
    await submitCredentials();

    const codeInput = await screen.findByLabelText(/authentication code/i);
    fireEvent.change(codeInput, { target: { value: '000000' } });
    clickSubmit(/^verify$/i);

    expect(await screen.findByText(/invalid verification code/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/authentication code/i)).toBeInTheDocument();
  });
});

describe('Login — forced MFA enrolment', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    me().mockRejectedValue(new Error('401'));
    (authApi.providers as ReturnType<typeof vi.fn>).mockResolvedValue({
      oidc: false,
      github: false,
      google: false,
    });
  });

  it('offers enrolment instead of authenticating when the server forces MFA', async () => {
    loginApi().mockResolvedValue({
      mfa_enrollment_required: true,
      message: 'MFA is required on this server.',
    });
    renderLogin();
    await submitCredentials();

    expect(await screen.findByText(/MFA is required on this server/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /set up mfa/i })).toBeInTheDocument();
    // No session exists yet — the app must not be authenticated. The only
    // /auth/me call is AuthProvider's own mount-time session probe.
    await waitFor(() => expect(me()).toHaveBeenCalledTimes(1));
  });

  it('reuses the existing enrolment flow and authenticates once it completes', async () => {
    loginApi().mockResolvedValue({
      mfa_enrollment_required: true,
      message: 'MFA is required on this server.',
    });
    (authApi.setupTotp as ReturnType<typeof vi.fn>).mockResolvedValue({
      secret: 'JBSWY3DPEHPK3PXP',
      provisioning_uri: 'otpauth://totp/MyACE:u@test.com?secret=JBSWY3DPEHPK3PXP',
    });
    (authApi.verifyTotp as ReturnType<typeof vi.fn>).mockResolvedValue({
      message: 'MFA enabled',
      mfa_enabled: true,
    });
    renderLogin();
    await submitCredentials();

    fireEvent.click(await screen.findByRole('button', { name: /set up mfa/i }));
    expect(await screen.findByText('JBSWY3DPEHPK3PXP')).toBeInTheDocument();

    me().mockResolvedValue(mockUser);
    fireEvent.change(screen.getByLabelText(/authentication code/i), {
      target: { value: '123456' },
    });
    clickSubmit(/^verify & enable$/i);

    await waitFor(() => expect(authApi.verifyTotp).toHaveBeenCalledWith('123456'));
    await waitFor(() => expect(me()).toHaveBeenCalled());
  });

  it('opens the enrolment step directly when the SSO callback redirects with ?enroll=1', async () => {
    const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    render(
      <QueryClientProvider client={queryClient}>
        <MemoryRouter initialEntries={['/login?enroll=1']}>
          <AuthProvider>
            <Login />
          </AuthProvider>
        </MemoryRouter>
      </QueryClientProvider>,
    );

    expect(await screen.findByText(/MFA is required on this server/i)).toBeInTheDocument();
  });
});
