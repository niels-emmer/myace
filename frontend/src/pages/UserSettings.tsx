import { useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import {
  User, Lock, Key, Plus, Trash2, Copy, Check, ExternalLink,
  Sun, Moon, Monitor, Smartphone, Shield, AlertTriangle, QrCode, Github, Bell,
} from 'lucide-react';
import { useTheme } from '../contexts/ThemeContext';
import { useAuth } from '../contexts/AuthContext';
import { authApi } from '../lib/api';
import type { ApiTokenCreate } from '../types';

export default function UserSettings() {
  const queryClient = useQueryClient();
  const { theme, setTheme } = useTheme();
  const { user, refresh } = useAuth();

  // Profile state
  const [displayName, setDisplayName] = useState(user?.display_name ?? '');
  const [email, setEmail] = useState(user?.email ?? '');
  const [profileMessage, setProfileMessage] = useState<string | null>(null);
  const [profileError, setProfileError] = useState<string | null>(null);

  // Password state
  const [currentPassword, setCurrentPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [passwordMessage, setPasswordMessage] = useState<string | null>(null);
  const [passwordError, setPasswordError] = useState<string | null>(null);

  // Token state
  const [showCreate, setShowCreate] = useState(false);
  const [tokenName, setTokenName] = useState('');
  const [newToken, setNewToken] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);
  const [copiedKey, setCopiedKey] = useState<string | null>(null);

  // MFA state
  const [mfaSecret, setMfaSecret] = useState<string | null>(null);
  const [mfaCode, setMfaCode] = useState('');
  const [mfaMessage, setMfaMessage] = useState<string | null>(null);
  const [mfaError, setMfaError] = useState<string | null>(null);

  // Delete account state
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
  const [deleteConfirmText, setDeleteConfirmText] = useState('');

  const { data: tokens, isLoading: tokensLoading } = useQuery({
    queryKey: ['tokens'],
    queryFn: () => authApi.listTokens(),
  });

  const { data: latestRelease } = useQuery({
    queryKey: ['github-latest-release'],
    queryFn: async () => {
      const res = await fetch('https://api.github.com/repos/niels-emmer/myace/releases/latest');
      if (!res.ok) throw new Error('Failed to fetch latest release');
      return res.json() as Promise<{ tag_name: string }>;
    },
    staleTime: 60 * 60 * 1000,
    retry: 1,
  });

  // Profile mutation
  const profileMutation = useMutation({
    mutationFn: (data: { display_name?: string; email?: string }) => authApi.updateProfile(data),
    onSuccess: () => {
      setProfileMessage('Profile updated');
      setProfileError(null);
      refresh();
    },
    onError: (err: Error) => {
      setProfileError(err.message);
      setProfileMessage(null);
    },
  });

  // Notification preferences — same profile-update endpoint, saved
  // immediately on toggle rather than gated behind the profile form's
  // Save button.
  const notifyMutation = useMutation({
    mutationFn: (data: { notify_on_download?: boolean; notify_on_comment?: boolean }) =>
      authApi.updateProfile(data),
    onSuccess: () => refresh(),
  });

  // Password mutation
  const passwordMutation = useMutation({
    mutationFn: (data: { current_password: string; new_password: string }) => authApi.changePassword(data),
    onSuccess: () => {
      setPasswordMessage('Password updated');
      setPasswordError(null);
      setCurrentPassword('');
      setNewPassword('');
      setConfirmPassword('');
    },
    onError: (err: Error) => {
      setPasswordError(err.message);
      setPasswordMessage(null);
    },
  });

  // Token mutations
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

  // MFA mutations
  const setupMfaMutation = useMutation({
    mutationFn: () => authApi.setupTotp(),
    onSuccess: (result) => {
      setMfaSecret(result.secret);
      setMfaMessage(null);
      setMfaError(null);
    },
    onError: (err: Error) => {
      setMfaError(err.message);
      setMfaMessage(null);
    },
  });

  const verifyMfaMutation = useMutation({
    mutationFn: (code: string) => authApi.verifyTotp(code),
    onSuccess: () => {
      setMfaMessage('MFA enabled successfully');
      setMfaError(null);
      setMfaCode('');
      setMfaSecret(null);
      refresh();
    },
    onError: (err: Error) => {
      setMfaError(err.message);
      setMfaMessage(null);
    },
  });

  const disableMfaMutation = useMutation({
    mutationFn: (code: string) => authApi.disableTotp(code),
    onSuccess: () => {
      setMfaMessage('MFA disabled');
      setMfaError(null);
      setMfaCode('');
      refresh();
    },
    onError: (err: Error) => {
      setMfaError(err.message);
      setMfaMessage(null);
    },
  });

  // Delete account mutation
  const deleteAccountMutation = useMutation({
    mutationFn: () => authApi.deleteAccount(),
    onSuccess: () => {
      refresh();
    },
  });

  const handleProfileSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const data: { display_name?: string; email?: string } = {};
    if (displayName !== user?.display_name) data.display_name = displayName;
    if (email !== user?.email) data.email = email;
    if (Object.keys(data).length === 0) {
      setProfileMessage('No changes to save');
      return;
    }
    profileMutation.mutate(data);
  };

  const handlePasswordSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (newPassword !== confirmPassword) {
      setPasswordError('Passwords do not match');
      return;
    }
    if (newPassword.length < 8) {
      setPasswordError('Password must be at least 8 characters');
      return;
    }
    passwordMutation.mutate({ current_password: currentPassword, new_password: newPassword });
  };

  const handleCreateToken = (e: React.FormEvent) => {
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

  const handleDeleteAccount = () => {
    if (deleteConfirmText === 'DELETE') {
      deleteAccountMutation.mutate();
    }
  };

  const backendOrigin = window.location.origin;
  const installCommand = 'pipx install "git+https://github.com/niels-emmer/myace.git#subdirectory=cli"';
  const loginCommand = `myace login --server ${backendOrigin} --token ${newToken ?? '<your-token>'}`;
  const pullCommand = 'myace pull --profile my-defaults --target opencode --path ~/.opencode/';

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-bold text-foreground">Settings</h1>
        <p className="text-muted-foreground mt-1">Manage your profile, security, and preferences</p>
      </div>

      {/* Profile */}
      <div className="bg-card rounded-xl border border-border p-6">
        <div className="flex items-center gap-2 mb-4">
          <User className="h-5 w-5 text-brand-600" />
          <h2 className="text-lg font-semibold text-card-foreground">Profile</h2>
        </div>
        <form onSubmit={handleProfileSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-foreground mb-1">Display Name</label>
            <input
              type="text"
              value={displayName}
              onChange={(e) => setDisplayName(e.target.value)}
              className="w-full px-3 py-2 bg-background text-foreground border border-input rounded-lg text-sm"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-foreground mb-1">Email</label>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="w-full px-3 py-2 bg-background text-foreground border border-input rounded-lg text-sm"
            />
          </div>
          {profileMessage && <p className="text-sm text-green-600">{profileMessage}</p>}
          {profileError && <p className="text-sm text-destructive">{profileError}</p>}
          <button
            type="submit"
            disabled={profileMutation.isPending}
            className="px-4 py-2 bg-brand-600 text-white rounded-lg hover:bg-brand-700 text-sm font-medium disabled:opacity-50"
          >
            {profileMutation.isPending ? 'Saving...' : 'Save Profile'}
          </button>
        </form>
      </div>

      {/* Notifications */}
      <div className="bg-card rounded-xl border border-border p-6">
        <div className="flex items-center gap-2 mb-4">
          <Bell className="h-5 w-5 text-brand-600" />
          <h2 className="text-lg font-semibold text-card-foreground">Notifications</h2>
        </div>
        <div className="space-y-3">
          <label className="flex items-start gap-3 cursor-pointer">
            <input
              type="checkbox"
              checked={user?.notify_on_download ?? false}
              onChange={(e) => notifyMutation.mutate({ notify_on_download: e.target.checked })}
              disabled={notifyMutation.isPending}
              className="mt-0.5"
            />
            <span>
              <span className="block text-sm font-medium text-foreground">
                Daily download digest
              </span>
              <span className="block text-xs text-muted-foreground">
                Get a daily email summarizing new downloads on your published collections.
              </span>
            </span>
          </label>
          <label className="flex items-start gap-3 cursor-pointer">
            <input
              type="checkbox"
              checked={user?.notify_on_comment ?? false}
              onChange={(e) => notifyMutation.mutate({ notify_on_comment: e.target.checked })}
              disabled={notifyMutation.isPending}
              className="mt-0.5"
            />
            <span>
              <span className="block text-sm font-medium text-foreground">New comments</span>
              <span className="block text-xs text-muted-foreground">
                Get an email as soon as someone comments on your published collections.
              </span>
            </span>
          </label>
          {notifyMutation.isError && (
            <p className="text-sm text-destructive">
              {(notifyMutation.error as Error).message}
            </p>
          )}
        </div>
      </div>

      {/* Password */}
      <div className="bg-card rounded-xl border border-border p-6">
        <div className="flex items-center gap-2 mb-4">
          <Lock className="h-5 w-5 text-brand-600" />
          <h2 className="text-lg font-semibold text-card-foreground">Password</h2>
        </div>
        <form onSubmit={handlePasswordSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-foreground mb-1">Current Password</label>
            <input
              type="password"
              value={currentPassword}
              onChange={(e) => setCurrentPassword(e.target.value)}
              className="w-full px-3 py-2 bg-background text-foreground border border-input rounded-lg text-sm"
              required
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-foreground mb-1">New Password</label>
            <input
              type="password"
              value={newPassword}
              onChange={(e) => setNewPassword(e.target.value)}
              className="w-full px-3 py-2 bg-background text-foreground border border-input rounded-lg text-sm"
              required
              minLength={8}
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-foreground mb-1">Confirm New Password</label>
            <input
              type="password"
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              className="w-full px-3 py-2 bg-background text-foreground border border-input rounded-lg text-sm"
              required
            />
          </div>
          {passwordMessage && <p className="text-sm text-green-600">{passwordMessage}</p>}
          {passwordError && <p className="text-sm text-destructive">{passwordError}</p>}
          <button
            type="submit"
            disabled={passwordMutation.isPending}
            className="px-4 py-2 bg-brand-600 text-white rounded-lg hover:bg-brand-700 text-sm font-medium disabled:opacity-50"
          >
            {passwordMutation.isPending ? 'Updating...' : 'Change Password'}
          </button>
        </form>
      </div>

      {/* MFA */}
      <div className="bg-card rounded-xl border border-border p-6">
        <div className="flex items-center gap-2 mb-4">
          <Smartphone className="h-5 w-5 text-brand-600" />
          <h2 className="text-lg font-semibold text-card-foreground">Multi-Factor Authentication</h2>
        </div>

        {mfaMessage && <p className="mb-4 text-sm text-green-600">{mfaMessage}</p>}
        {mfaError && <p className="mb-4 text-sm text-destructive">{mfaError}</p>}

        {user?.mfa_enabled ? (
          <div>
            <div className="flex items-center gap-2 p-3 bg-green-50 rounded-lg mb-4">
              <Shield className="h-4 w-4 text-green-600" />
              <span className="text-sm text-green-700 font-medium">MFA is enabled</span>
            </div>
            <div className="space-y-3">
              <p className="text-sm text-muted-foreground">
                Enter a TOTP code from your authenticator app to disable MFA.
              </p>
              <div className="flex gap-2">
                <input
                  type="text"
                  value={mfaCode}
                  onChange={(e) => setMfaCode(e.target.value)}
                  className="flex-1 px-3 py-2 bg-background text-foreground border border-input rounded-lg text-sm font-mono"
                  placeholder="000000"
                  maxLength={6}
                />
                <button
                  onClick={() => disableMfaMutation.mutate(mfaCode)}
                  disabled={disableMfaMutation.isPending || mfaCode.length !== 6}
                  className="px-4 py-2 bg-destructive text-white rounded-lg hover:bg-destructive/90 text-sm font-medium disabled:opacity-50"
                >
                  Disable MFA
                </button>
              </div>
            </div>
          </div>
        ) : mfaSecret ? (
          <div className="space-y-4">
            <div className="p-4 bg-amber-50 border border-amber-200 rounded-lg">
              <p className="text-sm font-medium text-amber-800 mb-2">
                Scan this QR code with your authenticator app (e.g., Google Authenticator, Authy)
              </p>
              <div className="flex justify-center mb-3">
                <QrCode className="h-32 w-32 text-amber-700" />
              </div>
              <p className="text-xs text-amber-700 mb-1">Or enter this secret manually:</p>
              <code className="block px-3 py-2 bg-card border border-amber-300 rounded text-sm font-mono break-all">
                {mfaSecret}
              </code>
            </div>
            <p className="text-sm text-muted-foreground">
              Enter the 6-digit code from your authenticator app to verify setup.
            </p>
            <div className="flex gap-2">
              <input
                type="text"
                value={mfaCode}
                onChange={(e) => setMfaCode(e.target.value)}
                className="flex-1 px-3 py-2 bg-background text-foreground border border-input rounded-lg text-sm font-mono"
                placeholder="000000"
                maxLength={6}
              />
              <button
                onClick={() => verifyMfaMutation.mutate(mfaCode)}
                disabled={verifyMfaMutation.isPending || mfaCode.length !== 6}
                className="px-4 py-2 bg-brand-600 text-white rounded-lg hover:bg-brand-700 text-sm font-medium disabled:opacity-50"
              >
                Verify & Enable
              </button>
            </div>
          </div>
        ) : (
          <div>
            <p className="text-sm text-muted-foreground mb-4">
              Add an extra layer of security by requiring a one-time code from your authenticator app when logging in.
            </p>
            <button
              onClick={() => setupMfaMutation.mutate()}
              disabled={setupMfaMutation.isPending}
              className="flex items-center gap-2 px-4 py-2 bg-brand-600 text-white rounded-lg hover:bg-brand-700 text-sm font-medium disabled:opacity-50"
            >
              <Smartphone className="h-4 w-4" />
              {setupMfaMutation.isPending ? 'Setting up...' : 'Set Up MFA'}
            </button>
          </div>
        )}
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

        {showCreate && (
          <form onSubmit={handleCreateToken} className="mb-4 p-4 bg-muted rounded-lg">
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
              <p className="mt-2 text-sm text-destructive">{(createMutation.error as Error).message}</p>
            )}
          </form>
        )}

        {newToken && (
          <div className="mb-4 p-4 bg-amber-50 border border-amber-200 rounded-lg">
            <p className="text-sm font-medium text-amber-800 mb-2">
              Token created! Copy it now — you won't see it again.
            </p>
            <div className="flex items-center gap-2">
              <code className="flex-1 px-3 py-2 bg-card border border-amber-300 rounded text-sm font-mono break-all">
                {newToken}
              </code>
              <button onClick={copyToken} className="p-2 hover:bg-amber-100 rounded transition-colors">
                {copied ? <Check className="h-4 w-4 text-green-600" /> : <Copy className="h-4 w-4 text-amber-700" />}
              </button>
            </div>
          </div>
        )}

        {tokensLoading ? (
          <p className="text-sm text-muted-foreground">Loading tokens...</p>
        ) : tokens && tokens.length > 0 ? (
          <div className="space-y-2">
            {tokens.map((token) => (
              <div key={token.id} className="flex items-center justify-between p-3 bg-muted rounded-lg">
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

      {/* CLI Setup */}
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

      {/* Delete Account */}
      <div className="bg-card rounded-xl border border-destructive/30 p-6">
        <div className="flex items-center gap-2 mb-4">
          <AlertTriangle className="h-5 w-5 text-destructive" />
          <h2 className="text-lg font-semibold text-card-foreground">Delete Account</h2>
        </div>
        <p className="text-sm text-muted-foreground mb-4">
          Permanently delete your account and all associated data. This action cannot be undone.
        </p>
        {!showDeleteConfirm ? (
          <button
            onClick={() => setShowDeleteConfirm(true)}
            className="px-4 py-2 bg-destructive text-white rounded-lg hover:bg-destructive/90 text-sm font-medium"
          >
            Delete My Account
          </button>
        ) : (
          <div className="space-y-3 p-4 bg-destructive/5 rounded-lg border border-destructive/20">
            <p className="text-sm font-medium text-destructive">
              Are you absolutely sure? This will delete all your collections, profiles, and tokens.
            </p>
            <p className="text-xs text-muted-foreground">
              Type <span className="font-mono font-bold text-foreground">DELETE</span> to confirm.
            </p>
            <input
              type="text"
              value={deleteConfirmText}
              onChange={(e) => setDeleteConfirmText(e.target.value)}
              className="w-full px-3 py-2 bg-background text-foreground border border-input rounded-lg text-sm font-mono"
              placeholder="Type DELETE to confirm"
            />
            <div className="flex gap-2">
              <button
                onClick={handleDeleteAccount}
                disabled={deleteConfirmText !== 'DELETE' || deleteAccountMutation.isPending}
                className="px-4 py-2 bg-destructive text-white rounded-lg hover:bg-destructive/90 text-sm font-medium disabled:opacity-50"
              >
                {deleteAccountMutation.isPending ? 'Deleting...' : 'Confirm Delete'}
              </button>
              <button
                onClick={() => { setShowDeleteConfirm(false); setDeleteConfirmText(''); }}
                className="px-4 py-2 bg-muted text-muted-foreground rounded-lg hover:bg-accent text-sm font-medium"
              >
                Cancel
              </button>
            </div>
            {deleteAccountMutation.isError && (
              <p className="text-sm text-destructive">{(deleteAccountMutation.error as Error).message}</p>
            )}
          </div>
        )}
      </div>

      {/* App Info */}
      <div className="flex items-center justify-center gap-2 text-xs text-muted-foreground">
        <span>MyACE v{latestRelease?.tag_name?.replace(/^v/, '') ?? '—'}</span>
        <span>|</span>
        <a
          href="https://github.com/niels-emmer/myace"
          target="_blank"
          rel="noopener noreferrer"
          className="inline-flex items-center gap-1 hover:text-foreground transition-colors"
        >
          <Github className="h-3.5 w-3.5" />
          GitHub repository
        </a>
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
