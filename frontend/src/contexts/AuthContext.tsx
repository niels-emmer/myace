import { createContext, useContext, useEffect, useState, type ReactNode } from 'react';
import { authApi } from '../lib/api';
import type { User } from '../types';

/**
 * Outcome of a password login attempt.
 *
 * `authenticated` means the server issued a session cookie and `user` is set.
 * `mfa_required` means the password step succeeded but **no session exists
 * yet** — the caller must complete the second factor before any authenticated
 * UI state is established.
 */
export type LoginOutcome =
  | { status: 'authenticated' }
  | { status: 'mfa_required'; mfaToken: string };

interface AuthContextValue {
  user: User | null;
  isLoading: boolean;
  login: (email: string, password: string) => Promise<LoginOutcome>;
  completeMfaLogin: (mfaToken: string, code: string) => Promise<void>;
  register: (email: string, password: string, displayName: string) => Promise<void>;
  logout: () => Promise<void>;
  loginWithProvider: (provider: string) => void;
  refresh: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  const refresh = async () => {
    try {
      const me = await authApi.me();
      setUser(me);
    } catch {
      setUser(null);
    }
  };

  useEffect(() => {
    (async () => {
      setIsLoading(true);
      await refresh();
      setIsLoading(false);
    })();
  }, []);

  const login = async (email: string, password: string): Promise<LoginOutcome> => {
    const result = await authApi.login({ email, password });
    if ('mfa_required' in result) {
      // A challenge object is not a session: do not touch `user`, or the app
      // would render an authenticated shell that every API call rejects.
      return { status: 'mfa_required', mfaToken: result.mfa_token };
    }
    setUser(result);
    return { status: 'authenticated' };
  };

  const completeMfaLogin = async (mfaToken: string, code: string) => {
    await authApi.loginMfa({ mfa_token: mfaToken, code });
    // The session cookie only exists now, so this is the first point at which
    // the app may treat the caller as authenticated.
    setUser(await authApi.me());
  };

  const register = async (email: string, password: string, displayName: string) => {
    const created = await authApi.register({ email, password, display_name: displayName });
    setUser(created);
  };

  const logout = async () => {
    await authApi.logout();
    setUser(null);
  };

  const loginWithProvider = (provider: string) => {
    authApi.loginWithProvider(provider);
  };

  return (
    <AuthContext.Provider value={{ user, isLoading, login, completeMfaLogin, register, logout, loginWithProvider, refresh }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used within an AuthProvider');
  return ctx;
}
