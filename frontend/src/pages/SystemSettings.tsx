import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  Shield, Database, RefreshCw, Users, Cpu, Globe, Lock, UserPlus,
  Smartphone, ToggleLeft, ToggleRight, ExternalLink, Trash2, AlertTriangle,
} from 'lucide-react';
import { useAuth } from '../contexts/AuthContext';
import { adminApi, authApi, adaptersApi, docCacheApi } from '../lib/api';
import type { UserAdminInfo } from '@/types';

const PROVIDER_DOCS: Record<string, { name: string; docs: string }> = {
  oidc: {
    name: 'OIDC (Authentik / Keycloak)',
    docs: 'https://goauthentik.io/docs/providers/oauth2/',
  },
  github: {
    name: 'GitHub',
    docs: 'https://docs.github.com/en/apps/oauth-apps/building-oauth-apps/creating-an-oauth-app',
  },
  google: {
    name: 'Google',
    docs: 'https://developers.google.com/identity/protocols/oauth2/web-server',
  },
};

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

  const removeUserMutation = useMutation({
    mutationFn: (id: string) => authApi.removeUser(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['admin-users'] });
      setUserToRemove(null);
    },
  });

  const [userToRemove, setUserToRemove] = useState<UserAdminInfo | null>(null);

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
          Enable or disable SSO providers. Provider credentials are configured via environment variables.
        </p>
        <div className="space-y-3">
          {Object.entries(PROVIDER_DOCS).map(([key, info]) => {
            const configured = !!providers?.[key as keyof typeof providers];
            const enabled = settings?.[key as keyof typeof settings] as boolean | undefined;
            return (
              <div key={key} className="flex items-center justify-between p-3 bg-muted rounded-lg">
                <div className="flex items-center gap-3">
                  <Globe className="h-4 w-4 text-muted-foreground" />
                  <div>
                    <p className="text-sm font-medium text-card-foreground">{info.name}</p>
                    <p className="text-xs text-muted-foreground">
                      {configured ? 'Configured via env' : 'Not configured'}
                    </p>
                  </div>
                </div>
                <div className="flex items-center gap-3">
                  <a
                    href={info.docs}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-xs text-brand-600 hover:text-brand-700 flex items-center gap-1"
                  >
                    Docs <ExternalLink className="h-3 w-3" />
                  </a>
                  <button
                    onClick={() => toggleSetting(`${key}_enabled`, enabled ?? true)}
                    className={`p-1.5 rounded-lg transition-colors ${
                      enabled !== false
                        ? 'text-green-600 hover:bg-green-50'
                        : 'text-muted-foreground hover:bg-accent'
                    }`}
                    title={enabled !== false ? 'Disable provider' : 'Enable provider'}
                  >
                    {enabled !== false ? <ToggleRight className="h-5 w-5" /> : <ToggleLeft className="h-5 w-5" />}
                  </button>
                </div>
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
                        <span className={`px-2 py-0.5 rounded text-xs font-medium ${
                          u.is_admin ? 'bg-purple-50 text-purple-700' : 'bg-muted text-muted-foreground'
                        }`}>
                          {u.is_admin ? 'Admin' : 'User'}
                        </span>
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
    </div>
  );
}
