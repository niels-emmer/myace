import { createContext, useContext, useEffect, useState, type ReactNode } from 'react';
import { authApi } from '../lib/api';
import type { User } from '../types';

interface AuthContextValue {
  user: User | null;
  isLoading: boolean;
  login: (email: string, password: string) => Promise<void>;
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

  const login = async (email: string, password: string) => {
    const loggedIn = await authApi.login({ email, password });
    setUser(loggedIn);
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
    <AuthContext.Provider value={{ user, isLoading, login, register, logout, loginWithProvider, refresh }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used within an AuthProvider');
  return ctx;
}
