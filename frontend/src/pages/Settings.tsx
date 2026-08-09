import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Key, Plus, Trash2, Copy, Check, ExternalLink, Shield, Sun, Moon, Monitor } from 'lucide-react';
import { useTheme } from '../contexts/ThemeContext';
import { authApi } from '../lib/api';
import type { ApiTokenCreate } from '../types';

export default function Settings() {
  const queryClient = useQueryClient();
  const { theme, setTheme } = useTheme();
  const [showCreate, setShowCreate] = useState(false);
  const [tokenName, setTokenName] = useState('');
  const [newToken, setNewToken] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);

  const { data: providers } = useQuery({
    queryKey: ['auth-providers'],
    queryFn: () => authApi.providers(),
  });

  const { data: tokens, isLoading } = useQuery({
    queryKey: ['tokens'],
    queryFn: () => authApi.listTokens(),
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

      {/* CLI Setup Instructions */}
      <div className="bg-card rounded-xl border border-border p-6">
        <div className="flex items-center gap-2 mb-4">
          <ExternalLink className="h-5 w-5 text-brand-600" />
          <h2 className="text-lg font-semibold text-card-foreground">CLI Setup</h2>
        </div>
        <div className="space-y-3 text-sm text-muted-foreground">
          <p>Install the CLI and authenticate with your API token:</p>
          <div className="bg-foreground text-background p-3 rounded-lg font-mono text-xs space-y-1">
            <p># Install the CLI</p>
            <p className="text-green-400">pip install myace-cli</p>
            <p></p>
            <p># Authenticate with your API token</p>
            <p className="text-green-400">myace login --server https://api.myace.localhost --token &lt;your-token&gt;</p>
            <p></p>
            <p># Pull a compiled profile</p>
            <p className="text-green-400">myace pull --profile my-defaults --target opencode --path ~/.opencode/</p>
          </div>
        </div>
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
