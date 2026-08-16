import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  Shield, Database, RefreshCw, Users, Cpu, Globe, Lock, UserPlus,
  Smartphone, ToggleLeft, ToggleRight, ExternalLink, Trash2, AlertTriangle,
  Mail, Send, Loader2, ChevronDown, ChevronRight, Copy, Check, FlaskConical,
} from 'lucide-react';
import { useAuth } from '../contexts/AuthContext';
import { adminApi, authApi, adaptersApi, docCacheApi } from '../lib/api';
import type { UserAdminInfo, SystemSettings, Role } from '@/types';

const inputClass =
  'w-full px-3 py-2 bg-background text-foreground border border-input rounded-lg text-sm ' +
  'focus:ring-2 focus:ring-brand-500 focus:border-brand-500';

type ProviderKey = 'oidc' | 'github' | 'google';

const PROVIDER_INFO: Record<ProviderKey, {
  name: string;
  docs: string;
  console: string | null;
  steps: string[];
}> = {
  oidc: {
    name: 'OIDC (Authentik / Keycloak)',
    docs: 'https://goauthentik.io/docs/providers/oauth2/',
    console: null,
    steps: [
      'In your identity provider (Authentik, Keycloak, etc.), create a new OAuth2/OIDC application.',
      'Set its redirect URI to the callback URL below, and note its issuer URL.',
      'Copy the Client ID, Client Secret, and Issuer URL into the fields below.',
    ],
  },
  github: {
    name: 'GitHub',
    docs: 'https://docs.github.com/en/apps/oauth-apps/building-oauth-apps/creating-an-oauth-app',
    console: 'https://github.com/settings/developers',
    steps: [
      'Go to GitHub → Settings → Developer settings → OAuth Apps → "New OAuth App".',
      'Set the "Authorization callback URL" to the callback URL below.',
      'Copy the generated Client ID and Client Secret into the fields below.',
    ],
  },
  google: {
    name: 'Google',
    docs: 'https://developers.google.com/identity/protocols/oauth2/web-server',
    console: 'https://console.cloud.google.com/apis/credentials',
    steps: [
      'Go to Google Cloud Console → APIs & Services → Credentials → "Create Credentials" → "OAuth client ID".',
      'Choose "Web application" and add the callback URL below under "Authorized redirect URIs".',
      'Copy the generated Client ID and Client Secret into the fields below.',
    ],
  },
};

interface ProviderCredentialsPanelProps {
  provider: ProviderKey;
  settings: SystemSettings;
  onSaved: () => void;
}

function ProviderCredentialsPanel({ provider, settings, onSaved }: ProviderCredentialsPanelProps) {
  const info = PROVIDER_INFO[provider];
  const secretSet = settings[`${provider}_client_secret_set`];

  const [clientId, setClientId] = useState(settings[`${provider}_client_id`] ?? '');
  const [clientSecret, setClientSecret] = useState('');
  const [issuerUrl, setIssuerUrl] = useState(settings.oidc_issuer_url ?? '');
  const [scopes, setScopes] = useState(settings.oidc_scopes ?? '');
  const [copied, setCopied] = useState(false);

  const redirectUrl = `${window.location.origin}/api/v1/auth/callback/${provider}`;

  const saveMutation = useMutation({
    mutationFn: () => {
      const payload: Record<string, unknown> = { [`${provider}_client_id`]: clientId };
      if (provider === 'oidc') {
        payload.oidc_issuer_url = issuerUrl;
        payload.oidc_scopes = scopes;
      }
      if (clientSecret) payload[`${provider}_client_secret`] = clientSecret;
      return adminApi.updateSettings(payload);
    },
    onSuccess: () => {
      setClientSecret('');
      onSaved();
    },
  });

  const clearSecretMutation = useMutation({
    mutationFn: () => adminApi.updateSettings({ [`${provider}_client_secret`]: '' }),
    onSuccess: onSaved,
  });

  const testMutation = useMutation({
    mutationFn: () =>
      adminApi.testOAuthProvider(provider, {
        client_id: clientId || undefined,
        client_secret: clientSecret || undefined,
        issuer_url: provider === 'oidc' ? issuerUrl || undefined : undefined,
        scopes: provider === 'oidc' ? scopes || undefined : undefined,
      }),
  });

  const copyRedirectUrl = () => {
    navigator.clipboard.writeText(redirectUrl);
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  };

  return (
    <div className="px-4 pb-4 pt-1 space-y-4 border-t border-border">
      <div>
        <p className="text-xs font-medium text-muted-foreground mb-2">Setup steps</p>
        <ol className="list-decimal list-inside space-y-1 text-sm text-card-foreground">
          {info.steps.map((step, i) => <li key={i}>{step}</li>)}
        </ol>
        <div className="flex items-center gap-3 mt-2">
          {info.console && (
            <a
              href={info.console}
              target="_blank"
              rel="noopener noreferrer"
              className="text-xs text-brand-600 hover:text-brand-700 flex items-center gap-1"
            >
              Open {info.name} console <ExternalLink className="h-3 w-3" />
            </a>
          )}
          <a
            href={info.docs}
            target="_blank"
            rel="noopener noreferrer"
            className="text-xs text-brand-600 hover:text-brand-700 flex items-center gap-1"
          >
            Docs <ExternalLink className="h-3 w-3" />
          </a>
        </div>
      </div>

      <div>
        <label className="block text-xs font-medium text-muted-foreground mb-1">
          Redirect / callback URL
        </label>
        <div className="flex items-center gap-2">
          <code className="flex-1 px-3 py-2 bg-muted rounded-lg text-xs text-foreground overflow-x-auto whitespace-nowrap">
            {redirectUrl}
          </code>
          <button
            type="button"
            onClick={copyRedirectUrl}
            className="p-2 text-muted-foreground hover:text-foreground hover:bg-muted rounded-lg"
            title="Copy"
          >
            {copied ? <Check className="h-4 w-4 text-green-600" /> : <Copy className="h-4 w-4" />}
          </button>
        </div>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
        <div>
          <label className="block text-xs font-medium text-muted-foreground mb-1">Client ID</label>
          <input
            type="text"
            value={clientId}
            onChange={(e) => setClientId(e.target.value)}
            className={inputClass}
          />
        </div>
        <div>
          <label className="block text-xs font-medium text-muted-foreground mb-1">Client Secret</label>
          <input
            type="password"
            value={clientSecret}
            onChange={(e) => setClientSecret(e.target.value)}
            placeholder={secretSet ? 'Configured — leave blank to keep' : ''}
            className={inputClass}
          />
          {secretSet && !clientSecret && (
            <button
              type="button"
              onClick={() => clearSecretMutation.mutate()}
              className="mt-1 text-xs text-destructive hover:underline"
            >
              Clear saved secret
            </button>
          )}
        </div>
        {provider === 'oidc' && (
          <>
            <div>
              <label className="block text-xs font-medium text-muted-foreground mb-1">Issuer URL</label>
              <input
                type="text"
                value={issuerUrl}
                onChange={(e) => setIssuerUrl(e.target.value)}
                placeholder="https://auth.example.com/application/o/myace/"
                className={inputClass}
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-muted-foreground mb-1">Scopes</label>
              <input
                type="text"
                value={scopes}
                onChange={(e) => setScopes(e.target.value)}
                placeholder="openid profile email"
                className={inputClass}
              />
            </div>
          </>
        )}
      </div>

      {testMutation.isSuccess && (
        <div className="p-3 bg-green-50 border border-green-200 rounded-lg text-sm text-green-800">
          {testMutation.data.message}
        </div>
      )}
      {testMutation.isError && (
        <div className="p-3 bg-destructive/10 border border-destructive/30 rounded-lg text-sm text-destructive">
          {(testMutation.error as Error).message}
        </div>
      )}
      {saveMutation.isSuccess && (
        <div className="p-3 bg-green-50 border border-green-200 rounded-lg text-sm text-green-800">
          {info.name} credentials saved.
        </div>
      )}
      {saveMutation.isError && (
        <div className="p-3 bg-destructive/10 border border-destructive/30 rounded-lg text-sm text-destructive">
          {(saveMutation.error as Error).message}
        </div>
      )}

      <div className="flex gap-2">
        <button
          onClick={() => testMutation.mutate()}
          disabled={testMutation.isPending || !clientId}
          className="flex items-center gap-2 px-3 py-1.5 bg-muted text-foreground border border-border rounded-lg hover:bg-accent disabled:opacity-50 text-sm font-medium"
        >
          {testMutation.isPending ? (
            <Loader2 className="h-4 w-4 animate-spin" />
          ) : (
            <FlaskConical className="h-4 w-4" />
          )}
          Test Connection
        </button>
        <button
          onClick={() => saveMutation.mutate()}
          disabled={saveMutation.isPending}
          className="px-3 py-1.5 bg-brand-600 text-white rounded-lg hover:bg-brand-700 disabled:opacity-50 text-sm font-medium"
        >
          Save
        </button>
      </div>
    </div>
  );
}

export default function SystemSettings() {
  const queryClient = useQueryClient();
  const { user } = useAuth();

  const { data: settings, isLoading } = useQuery({
    queryKey: ['system-settings'],
    queryFn: () => adminApi.getSettings(),
    enabled: !!user?.is_admin,
  });

  const { data: providers } = useQuery({
    queryKey: ['auth-providers'],
    queryFn: () => authApi.providers(),
  });

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

  const updateMutation = useMutation({
    mutationFn: (data: Record<string, unknown>) => adminApi.updateSettings(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['system-settings'] });
    },
  });

  const refreshCacheMutation = useMutation({
    mutationFn: () => docCacheApi.refresh(),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['doc-cache'] });
    },
  });

  const toggleSetting = (key: string, currentValue: boolean) => {
    updateMutation.mutate({ [key]: !currentValue });
  };

  const setUserActiveMutation = useMutation({
    mutationFn: ({ id, isActive }: { id: string; isActive: boolean }) =>
      authApi.setUserActive(id, isActive),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['admin-users'] });
    },
  });

  const setUserRoleMutation = useMutation({
    mutationFn: ({ id, role }: { id: string; role: Role }) =>
      authApi.setUserRole(id, role),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['admin-users'] });
    },
  });

  const removeUserMutation = useMutation({
    mutationFn: (id: string) => authApi.removeUser(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['admin-users'] });
      setUserToRemove(null);
    },
  });

  const [userToRemove, setUserToRemove] = useState<UserAdminInfo | null>(null);

  const toggleAdapterMutation = useMutation({
    mutationFn: ({ name, enabled }: { name: string; enabled: boolean }) =>
      adminApi.toggleAdapter(name, enabled),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['adapters'] });
    },
  });

  const [expandedProvider, setExpandedProvider] = useState<ProviderKey | null>(null);

  const onProviderCredentialsSaved = () => {
    queryClient.invalidateQueries({ queryKey: ['system-settings'] });
    queryClient.invalidateQueries({ queryKey: ['auth-providers'] });
  };

  const [smtpForm, setSmtpForm] = useState({
    smtp_enabled: false,
    smtp_host: '',
    smtp_port: 587,
    smtp_username: '',
    smtp_from_email: '',
    smtp_from_name: '',
    smtp_use_tls: true,
  });
  const [smtpPasswordInput, setSmtpPasswordInput] = useState('');
  const [smtpInitialized, setSmtpInitialized] = useState(false);

  // Adjust state during render (React's recommended alternative to an Effect
  // here — https://react.dev/learn/you-might-not-need-an-effect) rather than
  // setting it inside a useEffect, which would cascade an extra render.
  if (settings && !smtpInitialized) {
    setSmtpInitialized(true);
    setSmtpForm({
      smtp_enabled: settings.smtp_enabled,
      smtp_host: settings.smtp_host ?? '',
      smtp_port: settings.smtp_port ?? 587,
      smtp_username: settings.smtp_username ?? '',
      smtp_from_email: settings.smtp_from_email ?? '',
      smtp_from_name: settings.smtp_from_name ?? '',
      smtp_use_tls: settings.smtp_use_tls ?? true,
    });
  }

  const saveSmtpMutation = useMutation({
    mutationFn: () => {
      const payload: Record<string, unknown> = { ...smtpForm };
      if (smtpPasswordInput) payload.smtp_password = smtpPasswordInput;
      return adminApi.updateSettings(payload);
    },
    onSuccess: () => {
      setSmtpPasswordInput('');
      queryClient.invalidateQueries({ queryKey: ['system-settings'] });
    },
  });

  const clearSmtpPasswordMutation = useMutation({
    mutationFn: () => adminApi.updateSettings({ smtp_password: '' }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['system-settings'] });
    },
  });

  const testSmtpMutation = useMutation({
    mutationFn: () =>
      adminApi.testSmtp({
        host: smtpForm.smtp_host || undefined,
        port: smtpForm.smtp_port || undefined,
        username: smtpForm.smtp_username || undefined,
        password: smtpPasswordInput || undefined,
        from_email: smtpForm.smtp_from_email || undefined,
        from_name: smtpForm.smtp_from_name || undefined,
        use_tls: smtpForm.smtp_use_tls,
      }),
  });

  if (!user?.is_admin) {
    return (
      <div className="text-center py-12">
        <Lock className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
        <h2 className="text-lg font-semibold text-foreground">Admin Access Required</h2>
        <p className="text-muted-foreground mt-1">You need admin privileges to view system settings.</p>
      </div>
    );
  }

  if (isLoading) {
    return <p className="text-muted-foreground">Loading settings...</p>;
  }

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-bold text-foreground">System Settings</h1>
        <p className="text-muted-foreground mt-1">Manage authentication, security, and system-wide configuration</p>
      </div>

      {/* Auth Providers */}
      <div className="bg-card rounded-xl border border-border p-6">
        <div className="flex items-center gap-2 mb-4">
          <Shield className="h-5 w-5 text-brand-600" />
          <h2 className="text-lg font-semibold text-card-foreground">Authentication Providers</h2>
        </div>
        <p className="text-sm text-muted-foreground mb-4">
          Click a provider to configure its Client ID/Secret, or enable/disable it once configured
          (via .env or here).
        </p>
        <div className="space-y-3">
          {(Object.keys(PROVIDER_INFO) as ProviderKey[]).map((key) => {
            const info = PROVIDER_INFO[key];
            const configured = !!providers?.[key as keyof typeof providers];
            const enabled = settings?.[`${key}_enabled`];
            const isExpanded = expandedProvider === key;
            return (
              <div key={key} className="bg-muted rounded-lg overflow-hidden">
                <div className="flex items-center justify-between p-3">
                  <button
                    type="button"
                    onClick={() => setExpandedProvider(isExpanded ? null : key)}
                    className="flex items-center gap-3 flex-1 min-w-0 text-left"
                  >
                    {isExpanded ? (
                      <ChevronDown className="h-4 w-4 text-muted-foreground flex-shrink-0" />
                    ) : (
                      <ChevronRight className="h-4 w-4 text-muted-foreground flex-shrink-0" />
                    )}
                    <Globe className="h-4 w-4 text-muted-foreground flex-shrink-0" />
                    <div>
                      <p className="text-sm font-medium text-card-foreground">{info.name}</p>
                      <p className="text-xs text-muted-foreground">
                        {configured ? 'Configured' : 'Not configured'}
                      </p>
                    </div>
                  </button>
                  <button
                    onClick={() => toggleSetting(`${key}_enabled`, enabled ?? true)}
                    className={`p-1.5 rounded-lg transition-colors flex-shrink-0 ${
                      enabled !== false
                        ? 'text-green-600 hover:bg-green-100'
                        : 'text-muted-foreground hover:bg-accent'
                    }`}
                    title={enabled !== false ? 'Disable provider' : 'Enable provider'}
                  >
                    {enabled !== false ? <ToggleRight className="h-5 w-5" /> : <ToggleLeft className="h-5 w-5" />}
                  </button>
                </div>
                {isExpanded && settings && (
                  <ProviderCredentialsPanel
                    provider={key}
                    settings={settings}
                    onSaved={onProviderCredentialsSaved}
                  />
                )}
              </div>
            );
          })}
        </div>
      </div>

      {/* Registration */}
      <div className="bg-card rounded-xl border border-border p-6">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-2">
            <UserPlus className="h-5 w-5 text-brand-600" />
            <h2 className="text-lg font-semibold text-card-foreground">Registration</h2>
          </div>
          <button
            onClick={() => toggleSetting('allow_registration', settings?.allow_registration ?? true)}
            className={`flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm font-medium transition-colors ${
              settings?.allow_registration !== false
                ? 'bg-green-50 text-green-700 hover:bg-green-100'
                : 'bg-muted text-muted-foreground hover:bg-accent'
            }`}
          >
            {settings?.allow_registration !== false ? (
              <><ToggleRight className="h-4 w-4" /> Enabled</>
            ) : (
              <><ToggleLeft className="h-4 w-4" /> Disabled</>
            )}
          </button>
        </div>
        <p className="text-sm text-muted-foreground">
          When disabled, new users cannot register. Existing users can still log in.
        </p>
      </div>

      {/* Email (SMTP) */}
      <div className="bg-card rounded-xl border border-border p-6">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-2">
            <Mail className="h-5 w-5 text-brand-600" />
            <h2 className="text-lg font-semibold text-card-foreground">Email (SMTP)</h2>
          </div>
          <button
            onClick={() => setSmtpForm((f) => ({ ...f, smtp_enabled: !f.smtp_enabled }))}
            className={`flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm font-medium transition-colors ${
              smtpForm.smtp_enabled
                ? 'bg-green-50 text-green-700 hover:bg-green-100'
                : 'bg-muted text-muted-foreground hover:bg-accent'
            }`}
          >
            {smtpForm.smtp_enabled ? (
              <><ToggleRight className="h-4 w-4" /> Enabled</>
            ) : (
              <><ToggleLeft className="h-4 w-4" /> Disabled</>
            )}
          </button>
        </div>
        <p className="text-sm text-muted-foreground mb-4">
          Used to send password-reset emails. Values saved here override the SMTP_* env vars at runtime.
        </p>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          <div>
            <label className="block text-xs font-medium text-muted-foreground mb-1">Host</label>
            <input
              type="text"
              value={smtpForm.smtp_host}
              onChange={(e) => setSmtpForm((f) => ({ ...f, smtp_host: e.target.value }))}
              placeholder="smtp.example.com"
              className={inputClass}
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-muted-foreground mb-1">Port</label>
            <input
              type="number"
              value={smtpForm.smtp_port}
              onChange={(e) => setSmtpForm((f) => ({ ...f, smtp_port: Number(e.target.value) }))}
              className={inputClass}
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-muted-foreground mb-1">Username</label>
            <input
              type="text"
              value={smtpForm.smtp_username}
              onChange={(e) => setSmtpForm((f) => ({ ...f, smtp_username: e.target.value }))}
              className={inputClass}
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-muted-foreground mb-1">Password</label>
            <input
              type="password"
              value={smtpPasswordInput}
              onChange={(e) => setSmtpPasswordInput(e.target.value)}
              placeholder={settings?.smtp_password_set ? 'Configured — leave blank to keep' : ''}
              className={inputClass}
            />
            {settings?.smtp_password_set && !smtpPasswordInput && (
              <button
                type="button"
                onClick={() => clearSmtpPasswordMutation.mutate()}
                className="mt-1 text-xs text-destructive hover:underline"
              >
                Clear saved password
              </button>
            )}
          </div>
          <div>
            <label className="block text-xs font-medium text-muted-foreground mb-1">From email</label>
            <input
              type="email"
              value={smtpForm.smtp_from_email}
              onChange={(e) => setSmtpForm((f) => ({ ...f, smtp_from_email: e.target.value }))}
              placeholder="noreply@example.com"
              className={inputClass}
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-muted-foreground mb-1">From name</label>
            <input
              type="text"
              value={smtpForm.smtp_from_name}
              onChange={(e) => setSmtpForm((f) => ({ ...f, smtp_from_name: e.target.value }))}
              className={inputClass}
            />
          </div>
        </div>

        <label className="flex items-center gap-2 mt-3 text-sm text-card-foreground">
          <input
            type="checkbox"
            checked={smtpForm.smtp_use_tls}
            onChange={(e) => setSmtpForm((f) => ({ ...f, smtp_use_tls: e.target.checked }))}
            className="rounded border-input"
          />
          Use STARTTLS
        </label>

        {testSmtpMutation.isSuccess && (
          <div className="mt-4 p-3 bg-green-50 border border-green-200 rounded-lg text-sm text-green-800">
            {testSmtpMutation.data.message}
          </div>
        )}
        {testSmtpMutation.isError && (
          <div className="mt-4 p-3 bg-destructive/10 border border-destructive/30 rounded-lg text-sm text-destructive">
            {(testSmtpMutation.error as Error).message}
          </div>
        )}
        {saveSmtpMutation.isSuccess && (
          <div className="mt-4 p-3 bg-green-50 border border-green-200 rounded-lg text-sm text-green-800">
            SMTP settings saved.
          </div>
        )}
        {saveSmtpMutation.isError && (
          <div className="mt-4 p-3 bg-destructive/10 border border-destructive/30 rounded-lg text-sm text-destructive">
            {(saveSmtpMutation.error as Error).message}
          </div>
        )}

        <div className="flex gap-2 mt-4">
          <button
            onClick={() => testSmtpMutation.mutate()}
            disabled={testSmtpMutation.isPending || !smtpForm.smtp_host}
            className="flex items-center gap-2 px-3 py-1.5 bg-muted text-foreground border border-border rounded-lg hover:bg-accent disabled:opacity-50 text-sm font-medium"
          >
            {testSmtpMutation.isPending ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <Send className="h-4 w-4" />
            )}
            Send Test Email
          </button>
          <button
            onClick={() => saveSmtpMutation.mutate()}
            disabled={saveSmtpMutation.isPending}
            className="px-3 py-1.5 bg-brand-600 text-white rounded-lg hover:bg-brand-700 disabled:opacity-50 text-sm font-medium"
          >
            Save
          </button>
        </div>
      </div>

      {/* MFA Settings */}
      <div className="bg-card rounded-xl border border-border p-6">
        <div className="flex items-center gap-2 mb-4">
          <Smartphone className="h-5 w-5 text-brand-600" />
          <h2 className="text-lg font-semibold text-card-foreground">Multi-Factor Authentication</h2>
        </div>
        <div className="space-y-4">
          <div className="flex items-center justify-between p-3 bg-muted rounded-lg">
            <div>
              <p className="text-sm font-medium text-card-foreground">TOTP (Authenticator App)</p>
              <p className="text-xs text-muted-foreground">Allow users to set up time-based one-time passwords</p>
            </div>
            <button
              onClick={() => toggleSetting('mfa_enabled', settings?.mfa_enabled ?? false)}
              className={`p-1.5 rounded-lg transition-colors ${
                settings?.mfa_enabled
                  ? 'text-green-600 hover:bg-green-50'
                  : 'text-muted-foreground hover:bg-accent'
              }`}
            >
              {settings?.mfa_enabled ? <ToggleRight className="h-5 w-5" /> : <ToggleLeft className="h-5 w-5" />}
            </button>
          </div>
          {settings?.mfa_enabled && (
            <div className="flex items-center justify-between p-3 bg-muted rounded-lg">
              <div>
                <p className="text-sm font-medium text-card-foreground">Force MFA</p>
                <p className="text-xs text-muted-foreground">Require all users to have MFA configured</p>
              </div>
              <button
                onClick={() => toggleSetting('mfa_forced', settings?.mfa_forced ?? false)}
                className={`p-1.5 rounded-lg transition-colors ${
                  settings?.mfa_forced
                    ? 'text-amber-600 hover:bg-amber-50'
                    : 'text-muted-foreground hover:bg-accent'
                }`}
              >
                {settings?.mfa_forced ? <ToggleRight className="h-5 w-5" /> : <ToggleLeft className="h-5 w-5" />}
              </button>
            </div>
          )}
        </div>
      </div>

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
                  <th className="text-left py-2 pr-4 font-medium text-muted-foreground">Status</th>
                  <th className="text-right py-2 font-medium text-muted-foreground">Actions</th>
                </tr>
              </thead>
              <tbody>
                {allUsers.map((u) => {
                  const isSelf = u.id === user?.id;
                  return (
                    <tr key={u.id} className="border-b border-border/50">
                      <td className="py-2 pr-4 text-card-foreground">{u.display_name || '—'}</td>
                      <td className="py-2 pr-4 text-muted-foreground">{u.email}</td>
                      <td className="py-2 pr-4">
                        <select
                          value={u.role}
                          onChange={(e) =>
                            setUserRoleMutation.mutate({ id: u.id, role: e.target.value as Role })
                          }
                          disabled={isSelf || setUserRoleMutation.isPending}
                          title={
                            isSelf
                              ? 'Use your own account settings to change your own role'
                              : 'Change role'
                          }
                          className={`px-2 py-0.5 rounded text-xs font-medium border-0 disabled:opacity-30 disabled:cursor-not-allowed ${
                            u.role === 'admin'
                              ? 'bg-purple-50 text-purple-700'
                              : u.role === 'moderator'
                              ? 'bg-blue-50 text-blue-700'
                              : 'bg-muted text-muted-foreground'
                          }`}
                        >
                          <option value="user">User</option>
                          <option value="moderator">Moderator</option>
                          <option value="admin">Admin</option>
                        </select>
                      </td>
                      <td className="py-2 pr-4">
                        <span className={`px-2 py-0.5 rounded text-xs font-medium ${
                          u.is_active ? 'bg-green-50 text-green-700' : 'bg-red-50 text-red-700'
                        }`}>
                          {u.is_active ? 'Active' : 'Disabled'}
                        </span>
                      </td>
                      <td className="py-2">
                        <div className="flex items-center justify-end gap-1">
                          <button
                            onClick={() =>
                              setUserActiveMutation.mutate({ id: u.id, isActive: !u.is_active })
                            }
                            disabled={isSelf || setUserActiveMutation.isPending}
                            className={`p-1.5 rounded-lg transition-colors disabled:opacity-30 disabled:cursor-not-allowed ${
                              u.is_active
                                ? 'text-green-600 hover:bg-green-50'
                                : 'text-muted-foreground hover:bg-accent'
                            }`}
                            title={
                              isSelf
                                ? 'Use your own account settings to change your own status'
                                : u.is_active ? 'Disable user' : 'Enable user'
                            }
                          >
                            {u.is_active ? (
                              <ToggleRight className="h-5 w-5" />
                            ) : (
                              <ToggleLeft className="h-5 w-5" />
                            )}
                          </button>
                          <button
                            onClick={() => setUserToRemove(u)}
                            disabled={isSelf}
                            className="p-1.5 rounded-lg text-destructive hover:bg-destructive/10 transition-colors disabled:opacity-30 disabled:cursor-not-allowed"
                            title={
                              isSelf
                                ? 'Use your own account settings to delete your own account'
                                : 'Remove user'
                            }
                          >
                            <Trash2 className="h-4 w-4" />
                          </button>
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        ) : (
          <p className="text-sm text-muted-foreground">No users found.</p>
        )}
      </div>

      {userToRemove && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-card border border-border rounded-xl p-6 w-full max-w-sm space-y-4">
            <div className="flex items-start gap-3">
              <div className="p-2 bg-destructive/10 rounded-lg flex-shrink-0">
                <AlertTriangle className="h-5 w-5 text-destructive" />
              </div>
              <div>
                <h2 className="text-lg font-semibold text-card-foreground">
                  Remove {userToRemove.display_name || userToRemove.email}?
                </h2>
                <p className="text-sm text-muted-foreground mt-1">
                  This deactivates their account and all collections, profiles, and API tokens
                  they own. This is reversible by re-enabling the account, but is otherwise not
                  undoable from this screen.
                </p>
              </div>
            </div>

            {removeUserMutation.isError && (
              <p className="text-sm text-destructive">
                {(removeUserMutation.error as Error).message}
              </p>
            )}

            <div className="flex justify-end gap-3">
              <button
                onClick={() => setUserToRemove(null)}
                className="px-4 py-2 text-sm text-muted-foreground hover:text-accent-foreground"
              >
                Cancel
              </button>
              <button
                onClick={() => removeUserMutation.mutate(userToRemove.id)}
                disabled={removeUserMutation.isPending}
                className="px-4 py-2 bg-destructive text-white rounded-lg hover:bg-destructive/90 disabled:opacity-50 text-sm font-medium transition-colors"
              >
                {removeUserMutation.isPending ? 'Removing...' : 'Remove'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Adapter Registry */}
      <div className="bg-card rounded-xl border border-border p-6">
        <div className="flex items-center gap-2 mb-4">
          <Cpu className="h-5 w-5 text-brand-600" />
          <h2 className="text-lg font-semibold text-card-foreground">Adapter Registry</h2>
        </div>

        {adapters && adapters.length > 0 ? (
          <div className="space-y-2">
            {adapters.map((adapter) => (
              <div
                key={adapter.name}
                className={`flex items-center justify-between p-3 bg-muted rounded-lg ${
                  adapter.enabled ? '' : 'opacity-60'
                }`}
              >
                <div>
                  <p className="text-sm font-medium text-card-foreground">{adapter.name}</p>
                  <p className="text-xs text-muted-foreground mt-0.5">{adapter.description}</p>
                </div>
                <div className="flex items-center gap-3 ml-3">
                  <div className="flex flex-wrap gap-1.5 justify-end">
                    {adapter.targets.map((target) => (
                      <span
                        key={target}
                        className="px-2 py-0.5 bg-background text-muted-foreground rounded text-xs font-medium"
                      >
                        {target}
                      </span>
                    ))}
                  </div>
                  <button
                    onClick={() =>
                      toggleAdapterMutation.mutate({ name: adapter.name, enabled: !adapter.enabled })
                    }
                    className={`p-1.5 rounded-lg transition-colors flex-shrink-0 ${
                      adapter.enabled
                        ? 'text-green-600 hover:bg-green-100'
                        : 'text-muted-foreground hover:bg-accent'
                    }`}
                    title={adapter.enabled ? 'Disable adapter' : 'Enable adapter'}
                  >
                    {adapter.enabled ? (
                      <ToggleRight className="h-5 w-5" />
                    ) : (
                      <ToggleLeft className="h-5 w-5" />
                    )}
                  </button>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <p className="text-sm text-muted-foreground">No adapters registered.</p>
        )}
      </div>
    </div>
  );
}
