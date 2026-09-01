import { useState, useEffect } from 'react';
import { useNavigate, useSearchParams, Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { Loader2 } from 'lucide-react';
import { GithubIcon } from '../components/GithubIcon';
import { useAuth } from '../contexts/AuthContext';
import { authApi } from '../lib/api';

const inputClass =
  'w-full px-3 py-2 bg-background text-foreground border border-input rounded-lg text-sm focus:ring-2 focus:ring-brand-500 focus:border-brand-500';

export default function Login() {
  const { user, login, register } = useAuth();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const [mode, setMode] = useState<'login' | 'register'>(
    searchParams.get('mode') === 'register' ? 'register' : 'login'
  );
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [displayName, setDisplayName] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  // Already authenticated (fresh login, or an existing session) — leave /login.
  useEffect(() => {
    if (user) navigate('/', { replace: true });
  }, [user, navigate]);

  const { data: providers } = useQuery({
    queryKey: ['auth-providers'],
    queryFn: () => authApi.providers(),
  });

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      if (mode === 'login') {
        await login(email, password);
      } else {
        await register(email, password, displayName);
      }
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setSubmitting(false);
    }
  };

  const anyProviderConfigured = providers && (providers.oidc || providers.github || providers.google);

  return (
    <div className="min-h-screen flex flex-col items-center justify-center bg-background px-4 py-8">
      <div className="w-full max-w-sm space-y-6">
        <div className="flex flex-col items-center gap-2 text-center">
          <img src="/logo.png" alt="MyACE" className="h-[60px] w-[60px] sm:h-16 sm:w-16" />
          <h1 className="text-xl font-bold text-foreground">MyACE</h1>
          <p className="text-sm text-muted-foreground">Portable AI Agent Configs</p>
          <p className="text-sm text-muted-foreground">
            Store your AI agent rules, skills, and workflows once, then compile them into
            ready-to-use config files for Claude Code, OpenCode, Cursor, and more. Accounts are
            free — MyACE is still in testing, so expect some rough edges.
          </p>
        </div>

        <div className="bg-card rounded-xl border border-border p-6 space-y-4">
          <div className="flex gap-2">
            <button
              type="button"
              onClick={() => setMode('login')}
              className={`flex-1 px-3 py-2 rounded-lg border text-sm font-medium transition-colors ${
                mode === 'login'
                  ? 'border-brand-500 bg-brand-50 text-brand-700'
                  : 'border-border text-muted-foreground hover:border-input'
              }`}
            >
              Log in
            </button>
            <button
              type="button"
              onClick={() => setMode('register')}
              className={`flex-1 px-3 py-2 rounded-lg border text-sm font-medium transition-colors ${
                mode === 'register'
                  ? 'border-brand-500 bg-brand-50 text-brand-700'
                  : 'border-border text-muted-foreground hover:border-input'
              }`}
            >
              Register
            </button>
          </div>

          <form onSubmit={handleSubmit} className="space-y-3">
            {mode === 'register' && (
              <div>
                <label className="block text-sm font-medium text-foreground mb-1">Display Name</label>
                <input
                  type="text"
                  value={displayName}
                  onChange={(e) => setDisplayName(e.target.value)}
                  className={inputClass}
                  required
                />
              </div>
            )}
            <div>
              <label className="block text-sm font-medium text-foreground mb-1">Email</label>
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className={inputClass}
                required
                autoFocus
              />
            </div>
            <div>
              <div className="flex items-center justify-between mb-1">
                <label className="block text-sm font-medium text-foreground">Password</label>
                {mode === 'login' && (
                  <Link to="/reset-password" className="text-xs text-brand-600 hover:underline">
                    Forgot password?
                  </Link>
                )}
              </div>
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className={inputClass}
                minLength={mode === 'register' ? 8 : undefined}
                required
              />
            </div>

            {error && <p className="text-sm text-destructive">{error}</p>}

            <button
              type="submit"
              disabled={submitting}
              className="w-full flex items-center justify-center gap-2 px-4 py-2 bg-brand-600 text-white rounded-lg hover:bg-brand-700 disabled:opacity-50 text-sm font-medium transition-colors"
            >
              {submitting ? <Loader2 className="h-4 w-4 animate-spin" /> : null}
              {mode === 'login' ? 'Log in' : 'Create account'}
            </button>
          </form>

          {anyProviderConfigured && (
            <>
              <div className="flex items-center gap-3">
                <div className="h-px flex-1 bg-border" />
                <span className="text-xs text-muted-foreground">or continue with</span>
                <div className="h-px flex-1 bg-border" />
              </div>
              <div className="space-y-2">
                {providers?.github && (
                  <button
                    type="button"
                    onClick={() => authApi.loginWithProvider('github')}
                    className="w-full flex items-center justify-center gap-2 px-4 py-2 bg-muted border border-border rounded-lg text-sm text-foreground hover:bg-accent transition-colors"
                  >
                    <GithubIcon className="h-4 w-4" />
                    GitHub
                  </button>
                )}
                {providers?.google && (
                  <button
                    type="button"
                    onClick={() => authApi.loginWithProvider('google')}
                    className="w-full flex items-center justify-center gap-2 px-4 py-2 bg-muted border border-border rounded-lg text-sm text-foreground hover:bg-accent transition-colors"
                  >
                    Google
                  </button>
                )}
                {providers?.oidc && (
                  <button
                    type="button"
                    onClick={() => authApi.loginWithProvider('oidc')}
                    className="w-full flex items-center justify-center gap-2 px-4 py-2 bg-muted border border-border rounded-lg text-sm text-foreground hover:bg-accent transition-colors"
                  >
                    SSO (Authentik / Keycloak)
                  </button>
                )}
              </div>
            </>
          )}
        </div>
      </div>

      <a
        href="https://github.com/niels-emmer/myace"
        target="_blank"
        rel="noopener noreferrer"
        className="mt-8 flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground transition-colors"
      >
        <GithubIcon className="h-4 w-4" />
        View on GitHub
      </a>
    </div>
  );
}
