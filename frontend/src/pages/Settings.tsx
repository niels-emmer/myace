import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  Key, Plus, Trash2, Copy, Check, ExternalLink, Shield, Sun, Moon, Monitor,
  Database, RefreshCw, Users, Cpu,
} from 'lucide-react';
import { useTheme } from '../contexts/ThemeContext';
import { useAuth } from '../contexts/AuthContext';
import { authApi, adaptersApi, docCacheApi } from '../lib/api';
import type { ApiTokenCreate } from '../types';

export default function Settings() {
  const queryClient = useQueryClient();
  const { theme, setTheme } = useTheme();
  const { user } = useAuth();
  const [showCreate, setShowCreate] = useState(false);
  const [tokenName, setTokenName] = useState('');
  const [newToken, setNewToken] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);
  const [copiedKey, setCopiedKey] = useState<string | null>(null);

  const { data: providers } = useQuery({
    queryKey: ['auth-providers'],
    queryFn: () => authApi.providers(),
  });

  const { data: tokens, isLoading } = useQuery({
    queryKey: ['tokens'],
    queryFn: () => authApi.listTokens(),
  });

  // Admin-only queries
  const { data: docCacheEntries, isLoading: docCacheLoading } = useQuery({
    queryKey: ['doc-cache'],
    queryFn: () => docCacheApi.list(),
    enabled: !!user?.is_admin,
  });

  const { data: allUsers, isLoading: usersLoading } = useQuery({
    queryKey: ['admin-users'],
    queryFn: () => authApi.listUsers(),
    enabled: !!user?.is_admin,
  });

  const { data: adapters } = useQuery({
    queryKey: ['adapters'],
    queryFn: () => adaptersApi.list(),
    enabled: !!user?.is_admin,
  });

  const refreshCacheMutation = useMutation({
    mutationFn: () => docCacheApi.refresh(),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['doc-cache'] });
    },
  });

  const createMutation = useMutation({
    mutationFn: (data: ApiTokenCreate) => authApi.createToken(data),
    onSuccess: (result) => {
      setNewToken(result.token ?? null);
      setShowCreate(false);
      setTokenName('');
      queryClient.invalidateQueries({ queryKey: ['tokens'] });
    },
  });

  const revokeMutation = useMutation({
    mutationFn: (tokenId: string) => authApi.revokeToken(tokenId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['tokens'] });
    },
  });

  const handleCreate = (e: React.FormEvent) => {
    e.preventDefault();
    createMutation.mutate({ name: tokenName });
  };

  const copyToken = async () => {
    if (newToken) {
      await navigator.clipboard.writeText(newToken);
      setCopied(true);
      setTimeout(() => setCopied(false), 3000);
    }
  };

  const copyCommand = async (text: string, key: string) => {
    await navigator.clipboard.writeText(text);
    setCopiedKey(key);
    setTimeout(() => setCopiedKey(null), 2000);
  };

  const backendOrigin = window.location.origin;
  const installCommand = 'pip install "git+https://github.com/niels-emmer/myace.git#subdirectory=cli"';
  const loginCommand = `myace login --server ${backendOrigin} --token ${newToken ?? '<your-token>'}`;
  const pullCommand = 'myace pull --profile my-defaults --target opencode --path ~/.opencode/';

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-bold text-foreground">Settings</h1>
        <p className="text-muted-foreground mt-1">Manage your account, API tokens, and OIDC providers</p>
      </div>

      {/* OIDC Providers */}
      <div className="bg-card rounded-xl border border-border p-6">
        <div className="flex items-center gap-2 mb-4">
          <Shield className="h-5 w-5 text-brand-600" />
          <h2 className="text-lg font-semibold text-card-foreground">Authentication Providers</h2>
        </div>
        <div className="space-y-3">
          <ProviderRow name="OIDC (Authentik / Keycloak)" provider="oidc" configured={!!providers?.oidc} />
          <ProviderRow name="GitHub" provider="github" configured={!!providers?.github} />
          <ProviderRow name="Google" provider="google" configured={!!providers?.google} />
        </div>
      </div>

      {/* Appearance */}
      <div className="bg-card rounded-xl border border-border p-6">
        <div className="flex items-center gap-2 mb-4">
          {theme === 'dark' ? (
            <Moon className="h-5 w-5 text-brand-600" />
          ) : theme === 'light' ? (
            <Sun className="h-5 w-5 text-brand-600" />
          ) : (
            <Monitor className="h-5 w-5 text-brand-600" />
          )}
          <h2 className="text-lg font-semibold text-card-foreground">Appearance</h2>
        </div>
        <div className="flex gap-3">
          {(['light', 'dark', 'system'] as const).map((option) => (
            <button
              key={option}
              type="button"
              onClick={() => setTheme(option)}
              className={`flex items-center gap-2 px-4 py-2.5 rounded-lg border text-sm font-medium transition-colors capitalize ${
                theme === option
                  ? 'border-brand-500 bg-brand-50 text-brand-700'
                  : 'border-border text-muted-foreground hover:border-input hover:text-accent-foreground'
              }`}
            >
              {option === 'light' && <Sun className="h-4 w-4" />}
              {option === 'dark' && <Moon className="h-4 w-4" />}
              {option === 'system' && <Monitor className="h-4 w-4" />}
              {option}
            </button>
          ))}
        </div>
      </div>

      {/* API Tokens */}
      <div className="bg-card rounded-xl border border-border p-6">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-2">
            <Key className="h-5 w-5 text-brand-600" />
            <h2 className="text-lg font-semibold text-card-foreground">API Tokens</h2>
          </div>
          <button
            onClick={() => setShowCreate(!showCreate)}
            className="flex items-center gap-2 px-3 py-1.5 bg-brand-600 text-white rounded-lg hover:bg-brand-700 text-sm font-medium"
          >
            <Plus className="h-4 w-4" />
            New Token
          </button>
        </div>

        {/* Create Token Form */}
        {showCreate && (
          <form onSubmit={handleCreate} className="mb-4 p-4 bg-muted rounded-lg">
            <label className="block text-sm font-medium text-foreground mb-1">Token Name</label>
            <div className="flex gap-2">
              <input
                type="text"
                value={tokenName}
                onChange={(e) => setTokenName(e.target.value)}
                className="flex-1 px-3 py-2 bg-background text-foreground border border-input rounded-lg text-sm"
                placeholder="e.g., my-cli-token"
                required
              />
              <button
                type="submit"
                disabled={createMutation.isPending}
                className="px-4 py-2 bg-brand-600 text-white rounded-lg hover:bg-brand-700 text-sm font-medium disabled:opacity-50"
              >
                {createMutation.isPending ? 'Creating...' : 'Create'}
              </button>
            </div>
            {createMutation.isError && (
              <p className="mt-2 text-sm text-destructive">
                {(createMutation.error as Error).message}
              </p>
            )}
          </form>
        )}

        {revokeMutation.isError && (
          <p className="mb-4 text-sm text-destructive">
            {(revokeMutation.error as Error).message}
          </p>
        )}

        {/* New Token Display */}
        {newToken && (
          <div className="mb-4 p-4 bg-amber-50 border border-amber-200 rounded-lg">
            <p className="text-sm font-medium text-amber-800 mb-2">
              Token created! Copy it now — you won't see it again.
            </p>
            <div className="flex items-center gap-2">
              <code className="flex-1 px-3 py-2 bg-card border border-amber-300 rounded text-sm font-mono break-all">
                {newToken}
              </code>
              <button
                onClick={copyToken}
                className="p-2 hover:bg-amber-100 rounded transition-colors"
              >
                {copied ? (
                  <Check className="h-4 w-4 text-green-600" />
                ) : (
                  <Copy className="h-4 w-4 text-amber-700" />
                )}
              </button>
            </div>
          </div>
        )}

        {/* Token List */}
        {isLoading ? (
          <p className="text-sm text-muted-foreground">Loading tokens...</p>
        ) : tokens && tokens.length > 0 ? (
          <div className="space-y-2">
            {tokens.map((token) => (
              <div
                key={token.id}
                className="flex items-center justify-between p-3 bg-muted rounded-lg"
              >
                <div>
                  <p className="text-sm font-medium text-card-foreground">{token.name}</p>
                  <p className="text-xs text-muted-foreground">
                    Prefix: {token.token_prefix}...
                    {' | '}Expires: {new Date(token.expires_at).toLocaleDateString()}
                    {token.last_used_at && ` | Last used: ${new Date(token.last_used_at).toLocaleDateString()}`}
                  </p>
                </div>
                <button
                  onClick={() => revokeMutation.mutate(token.id)}
                  className="p-2 text-destructive hover:bg-destructive/10 rounded transition-colors"
                  title="Revoke token"
                >
                  <Trash2 className="h-4 w-4" />
                </button>
              </div>
            ))}
          </div>
        ) : (
          <p className="text-sm text-muted-foreground">No API tokens yet. Create one for CLI access.</p>
        )}
      </div>

      {/* ─── Admin Sections ──────────────────────────────────────── */}
      {user?.is_admin && (
        <>
          {/* Doc Cache Management */}
          <div className="bg-card rounded-xl border border-border p-6">
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-2">
                <Database className="h-5 w-5 text-brand-600" />
                <h2 className="text-lg font-semibold text-card-foreground">Documentation Cache</h2>
              </div>
              <button
                onClick={() => refreshCacheMutation.mutate()}
                disabled={refreshCacheMutation.isPending}
                className="flex items-center gap-2 px-3 py-1.5 bg-brand-600 text-white rounded-lg hover:bg-brand-700 disabled:opacity-50 text-sm font-medium"
              >
                <RefreshCw className={`h-4 w-4 ${refreshCacheMutation.isPending ? 'animate-spin' : ''}`} />
                Refresh All
              </button>
            </div>

            {refreshCacheMutation.isSuccess && (
              <div className="mb-4 p-3 bg-green-50 border border-green-200 rounded-lg text-sm text-green-800">
                Refreshed {refreshCacheMutation.data.total_updated} cache entries
                {Object.entries(refreshCacheMutation.data.refreshed).length > 0 && (
                  <span>
                    {' ('}
                    {Object.entries(refreshCacheMutation.data.refreshed)
                      .filter(([, count]) => count > 0)
                      .map(([fw, count]) => `${fw}: ${count}`)
                      .join(', ')}
                    )
                  </span>
                )}
              </div>
            )}

            {refreshCacheMutation.isError && (
              <div className="mb-4 p-3 bg-destructive/10 border border-destructive/30 rounded-lg text-sm text-destructive">
                Refresh failed: {(refreshCacheMutation.error as Error).message}
              </div>
            )}

            {docCacheLoading ? (
              <p className="text-sm text-muted-foreground">Loading cache entries...</p>
            ) : docCacheEntries && docCacheEntries.length > 0 ? (
              <div className="space-y-2">
                {docCacheEntries.map((entry) => (
                  <div key={entry.id} className="flex items-center justify-between p-3 bg-muted rounded-lg">
                    <div className="min-w-0 flex-1">
                      <p className="text-sm font-medium text-card-foreground">{entry.framework}</p>
                      <p className="text-xs text-muted-foreground truncate">{entry.url}</p>
                      <p className="text-xs text-muted-foreground mt-0.5">
                        Fetched: {new Date(entry.fetched_at).toLocaleDateString()}
                        {' | '}Expires: {new Date(entry.expires_at).toLocaleDateString()}
                      </p>
                    </div>
                    <span className={`ml-3 px-2 py-0.5 rounded text-xs font-medium ${
                      new Date(entry.expires_at) > new Date()
                        ? 'bg-green-50 text-green-700'
                        : 'bg-amber-50 text-amber-700'
                    }`}>
                      {new Date(entry.expires_at) > new Date() ? 'Valid' : 'Expired'}
                    </span>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-sm text-muted-foreground">No cached documentation entries.</p>
            )}
          </div>

          {/* User Management */}
          <div className="bg-card rounded-xl border border-border p-6">
            <div className="flex items-center gap-2 mb-4">
              <Users className="h-5 w-5 text-brand-600" />
              <h2 className="text-lg font-semibold text-card-foreground">Users</h2>
            </div>

            {usersLoading ? (
              <p className="text-sm text-muted-foreground">Loading users...</p>
            ) : allUsers && allUsers.length > 0 ? (
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-border">
                      <th className="text-left py-2 pr-4 font-medium text-muted-foreground">Name</th>
                      <th className="text-left py-2 pr-4 font-medium text-muted-foreground">Email</th>
                      <th className="text-left py-2 pr-4 font-medium text-muted-foreground">Role</th>
                      <th className="text-left py-2 font-medium text-muted-foreground">Status</th>
                    </tr>
                  </thead>
                  <tbody>
                    {allUsers.map((u) => (
                      <tr key={u.id} className="border-b border-border/50">
                        <td className="py-2 pr-4 text-card-foreground">{u.display_name || '—'}</td>
                        <td className="py-2 pr-4 text-muted-foreground">{u.email}</td>
                        <td className="py-2 pr-4">
                          <span className={`px-2 py-0.5 rounded text-xs font-medium ${
                            u.is_admin ? 'bg-purple-50 text-purple-700' : 'bg-muted text-muted-foreground'
                          }`}>
                            {u.is_admin ? 'Admin' : 'User'}
                          </span>
                        </td>
                        <td className="py-2">
                          <span className={`px-2 py-0.5 rounded text-xs font-medium ${
                            u.is_active ? 'bg-green-50 text-green-700' : 'bg-red-50 text-red-700'
                          }`}>
                            {u.is_active ? 'Active' : 'Disabled'}
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <p className="text-sm text-muted-foreground">No users found.</p>
            )}
          </div>

          {/* Adapter Registry */}
          <div className="bg-card rounded-xl border border-border p-6">
            <div className="flex items-center gap-2 mb-4">
              <Cpu className="h-5 w-5 text-brand-600" />
              <h2 className="text-lg font-semibold text-card-foreground">Adapter Registry</h2>
            </div>

            {adapters && adapters.length > 0 ? (
              <div className="space-y-2">
                {adapters.map((adapter) => (
                  <div key={adapter.name} className="flex items-center justify-between p-3 bg-muted rounded-lg">
                    <div>
                      <p className="text-sm font-medium text-card-foreground">{adapter.name}</p>
                      <p className="text-xs text-muted-foreground mt-0.5">{adapter.description}</p>
                    </div>
                    <div className="flex flex-wrap gap-1.5 ml-3">
                      {adapter.targets.map((target) => (
                        <span
                          key={target}
                          className="px-2 py-0.5 bg-background text-muted-foreground rounded text-xs font-medium"
                        >
                          {target}
                        </span>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-sm text-muted-foreground">No adapters registered.</p>
            )}
          </div>
        </>
      )}

      {/* CLI Setup Instructions */}
      <div className="bg-card rounded-xl border border-border p-6">
        <div className="flex items-center gap-2 mb-4">
          <ExternalLink className="h-5 w-5 text-brand-600" />
          <h2 className="text-lg font-semibold text-card-foreground">CLI Setup</h2>
        </div>
        <div className="space-y-3 text-sm text-muted-foreground">
          <p>
            Install the CLI and authenticate against{' '}
            <span className="font-mono text-foreground">{backendOrigin}</span>:
          </p>
          {!newToken && (
            <p className="text-amber-700">
              Create a token above first, then this login command will fill in for you automatically.
            </p>
          )}
          <CommandLine label="# Install the CLI" command={installCommand} copyKey="install" copiedKey={copiedKey} onCopy={copyCommand} />
          <CommandLine label="# Authenticate with your API token" command={loginCommand} copyKey="login" copiedKey={copiedKey} onCopy={copyCommand} />
          <CommandLine label="# Pull a compiled profile" command={pullCommand} copyKey="pull" copiedKey={copiedKey} onCopy={copyCommand} />
        </div>
      </div>
    </div>
  );
}

function CommandLine({
  label,
  command,
  copyKey,
  copiedKey,
  onCopy,
}: {
  label: string;
  command: string;
  copyKey: string;
  copiedKey: string | null;
  onCopy: (text: string, key: string) => void;
}) {
  return (
    <div>
      <p className="text-xs text-muted-foreground mb-1">{label}</p>
      <div className="flex items-center justify-between gap-2 bg-foreground text-background p-3 rounded-lg font-mono text-xs">
        <code className="break-all">{command}</code>
        <button
          onClick={() => onCopy(command, copyKey)}
          className="shrink-0 p-1 hover:bg-background/10 rounded transition-colors"
        >
          {copiedKey === copyKey ? (
            <Check className="h-4 w-4 text-green-400" />
          ) : (
            <Copy className="h-4 w-4 text-background/70" />
          )}
        </button>
      </div>
    </div>
  );
}

function ProviderRow({
  name,
  provider,
  configured,
}: {
  name: string;
  provider: string;
  configured: boolean;
}) {
  const content = (
    <>
      <div className="flex items-center gap-3">
        <div className={`h-2 w-2 rounded-full ${configured ? 'bg-green-400' : 'bg-muted-foreground/30'}`} />
        <span className="text-sm text-foreground">{name}</span>
      </div>
      <span className={`text-xs font-medium ${configured ? 'text-green-600' : 'text-muted-foreground'}`}>
        {configured ? 'Sign in' : 'Not configured'}
      </span>
    </>
  );

  if (!configured) {
    return <div className="flex items-center justify-between p-3 bg-muted rounded-lg opacity-60">{content}</div>;
  }

  return (
    <button
      type="button"
      onClick={() => authApi.loginWithProvider(provider)}
      className="w-full flex items-center justify-between p-3 bg-muted rounded-lg hover:bg-accent transition-colors"
    >
      {content}
    </button>
  );
}
