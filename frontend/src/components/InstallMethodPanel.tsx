import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import {
  AlertTriangle,
  Check,
  Copy,
  Download,
  File as FileIcon,
  Folder,
  ShieldCheck,
  Terminal,
  X,
} from 'lucide-react';
import { profilesApi } from '../lib/api';
import { permissionFileStatus } from '../lib/permissions';
import {
  companionApi,
  fetchCompanionHealth,
  installsApi,
} from '../lib/setupApi';
import type { CompileResult } from '../types';
import type {
  CompanionApplyPreview,
  CompanionApplyResult,
  InstallLocation,
  InstallMethod,
  ProfileInstall,
} from '../types/setup';

type MethodTab = 'download' | 'cli' | 'direct';

/** POSIX single-quote escaping: a profile name is attacker-controlled free text. */
function shellQuote(value: string): string {
  return `'${value.replace(/'/g, `'\\''`)}'`;
}

const METHOD_LABELS: Record<MethodTab, string> = {
  download: 'Download',
  cli: 'CLI',
  direct: 'Install directly',
};

interface InstallMethodPanelProps {
  profileId: string;
  profileName: string;
  target: string;
  location: InstallLocation;
  /** Called after a claim is recorded successfully. */
  onClaimed?: (claim: ProfileInstall) => void;
  /** Wizard use: tighter spacing. */
  compact?: boolean;
}

/**
 * Per-target install methods: Download (.zip), CLI, and — only when the local
 * companion reports `apply.supported` — a diff-first direct write.
 *
 * Every successful action POSTs an install *claim*; nothing here ever claims
 * verification. `SyncStatus` (from `myace check --report`) is the only verified
 * source — see docs/onboarding-wizard.md.
 */
export default function InstallMethodPanel({
  profileId,
  profileName,
  target,
  location,
  onClaimed,
  compact = false,
}: InstallMethodPanelProps) {
  const [method, setMethod] = useState<MethodTab>('download');
  const [preview, setPreview] = useState<CompileResult | null>(null);
  const [previewLoading, setPreviewLoading] = useState(false);
  const [downloading, setDownloading] = useState(false);
  const [copied, setCopied] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [claimError, setClaimError] = useState<string | null>(null);
  const [applyPreview, setApplyPreview] = useState<CompanionApplyPreview | null>(null);
  const [applyResult, setApplyResult] = useState<CompanionApplyResult | null>(null);
  const [applying, setApplying] = useState(false);
  const [warningsDismissed, setWarningsDismissed] = useState(false);

  const companion = useQuery({
    queryKey: ['companion-health-apply'],
    queryFn: fetchCompanionHealth,
    retry: 1,
    staleTime: 15_000,
    refetchInterval: 30_000,
  });

  const applyCapability = companion.data?.apply;
  const directSupported =
    Boolean(applyCapability?.supported) &&
    Boolean(applyCapability?.targets.includes(target)) &&
    (location === 'project' || Boolean(applyCapability?.machine_targets.includes(target)));

  // If the companion stops advertising apply (or the target/location changes),
  // fall back to Download rather than rendering an empty panel.
  const activeMethod: MethodTab = method === 'direct' && !directSupported ? 'download' : method;

  const cliCommand = `myace pull --profile ${shellQuote(profileName)} --target ${shellQuote(target)}`;
  const verifyCommand = `myace check --target ${shellQuote(target)} --report`;

  const claim = async (claimMethod: InstallMethod) => {
    setClaimError(null);
    try {
      const result = await installsApi.claim(profileId, {
        target,
        location,
        method: claimMethod,
      });
      onClaimed?.(result);
    } catch (err) {
      // The file operation succeeded; failing to record the claim must not
      // look like a failed install. Surface it as a separate, softer message.
      setClaimError((err as Error).message);
    }
  };

  const copyToClipboard = async (text: string, key: string) => {
    await navigator.clipboard.writeText(text);
    setCopied(key);
    setTimeout(() => setCopied(null), 2000);
  };

  const handleCopyCli = async () => {
    await copyToClipboard(cliCommand, 'cli');
    await claim('cli');
  };

  const handleCopyVerify = async () => {
    await copyToClipboard(verifyCommand, 'verify');
  };

  const handleDownloadZip = async () => {
    setDownloading(true);
    setError(null);
    try {
      const res = await fetch('/api/v1/profiles/compile/zip', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'same-origin',
        body: JSON.stringify({ profile_id: profileId, target }),
      });
      if (!res.ok) throw new Error(`Download failed (${res.status})`);
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `${profileName}-${target}.zip`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      // Deferred revocation so Safari's native Save As dialog can read the blob.
      setTimeout(() => URL.revokeObjectURL(url), 1000);
      await claim('zip');
    } catch (err) {
      setError(
        err instanceof Error && err.message.startsWith('Download failed')
          ? 'Could not download the zip. Try again.'
          : (err as Error).message,
      );
    } finally {
      setDownloading(false);
    }
  };

  const handlePreviewFiles = async () => {
    setPreviewLoading(true);
    setError(null);
    try {
      const result = await profilesApi.compile({ profile_id: profileId, target });
      setPreview(result);
      setWarningsDismissed(false);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setPreviewLoading(false);
    }
  };

  const handleApplyPreview = async () => {
    if (!companion.data) return;
    setApplying(true);
    setError(null);
    try {
      const result = await companionApi.previewApply(companion.data.baseUrl, {
        profile_id: profileId,
        target,
        location,
      });
      setApplyPreview(result);
      setApplyResult(null);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setApplying(false);
    }
  };

  const handleApplyConfirm = async () => {
    if (!companion.data || !applyPreview) return;
    setApplying(true);
    setError(null);
    try {
      const result = await companionApi.apply(companion.data.baseUrl, {
        profile_id: profileId,
        target,
        location,
        preview_id: applyPreview.preview_id,
        confirm: true,
      });
      setApplyResult(result);
      setApplyPreview(null);
      await claim('apply');
    } catch (err) {
      setError((err as Error).message);
      // The preview token is single-use; a failed apply needs a fresh preview.
      setApplyPreview(null);
    } finally {
      setApplying(false);
    }
  };

  const warnings = preview?.warnings ?? [];

  return (
    <div className={compact ? 'space-y-3' : 'space-y-4'}>
      {/* Method tabs */}
      <div className="flex flex-wrap gap-1.5 border-b border-border pb-2">
        {(Object.keys(METHOD_LABELS) as MethodTab[])
          // Direct install only exists when the companion advertises apply for
          // this target/location — otherwise the method is absent, not a
          // disabled tease (docs/onboarding-wizard.md).
          .filter((tab) => tab !== 'direct' || directSupported)
          .map((tab) => (
            <button
              key={tab}
              type="button"
              onClick={() => setMethod(tab)}
              className={`rounded-lg px-3 py-1.5 text-sm font-medium transition-colors ${
                method === tab
                  ? 'bg-brand-50 text-brand-700'
                  : 'text-muted-foreground hover:bg-accent'
              }`}
            >
              {METHOD_LABELS[tab]}
            </button>
          ))}
      </div>

      {error && (
        <div className="rounded-lg border border-destructive/30 bg-destructive/10 p-3 text-sm text-destructive">
          {error}
        </div>
      )}

      {claimError && (
        <p className="text-xs text-muted-foreground">
          Installed, but the claim could not be recorded: {claimError}
        </p>
      )}

      {activeMethod === 'download' && (
        <div className="flex flex-wrap items-center gap-3">
          <button
            type="button"
            onClick={handleDownloadZip}
            disabled={downloading}
            className="flex items-center gap-2 rounded-lg bg-brand-600 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-brand-700 disabled:opacity-50"
          >
            <Download className="h-4 w-4" />
            {downloading ? 'Preparing zip…' : 'Download .zip'}
          </button>
          <span className="text-xs text-muted-foreground">
            Unzip in the install root shown above. Counts as “installed, not verified”.
          </span>
        </div>
      )}

      {activeMethod === 'cli' && (
        <div className="space-y-2">
          <div className="flex items-center justify-between gap-2 rounded-lg bg-muted p-3">
            <code className="min-w-0 flex-1 break-all text-sm text-foreground">{cliCommand}</code>
            <button
              type="button"
              onClick={handleCopyCli}
              aria-label="Copy CLI command"
              className="shrink-0 rounded p-1.5 transition-colors hover:bg-accent"
            >
              {copied === 'cli' ? (
                <Check className="h-4 w-4 text-green-600" />
              ) : (
                <Copy className="h-4 w-4 text-muted-foreground" />
              )}
            </button>
          </div>
          <p className="flex items-center gap-1.5 text-xs text-muted-foreground">
            <Terminal className="h-3.5 w-3.5" />
            Run it in the install root. Then verify with{' '}
            <button
              type="button"
              onClick={handleCopyVerify}
              className="font-mono text-brand-600 hover:underline"
            >
              {copied === 'verify' ? 'copied' : verifyCommand}
            </button>
          </p>
        </div>
      )}

      {activeMethod === 'direct' && directSupported && (
        <div className="space-y-3">
          {!applyPreview && !applyResult && (
            <div className="flex flex-wrap items-center gap-3">
              <button
                type="button"
                onClick={handleApplyPreview}
                disabled={applying}
                className="flex items-center gap-2 rounded-lg border border-border px-4 py-2 text-sm font-medium text-foreground transition-colors hover:bg-accent disabled:opacity-50"
              >
                <ShieldCheck className="h-4 w-4" />
                {applying ? 'Checking files…' : 'Preview changes'}
              </button>
              <span className="text-xs text-muted-foreground">
                Nothing is written until you confirm the diff.
              </span>
            </div>
          )}

          {applyPreview && (
            <div className="space-y-3 rounded-lg border border-border p-3">
              <p className="text-sm text-foreground">
                {applyPreview.files.filter((f) => f.action !== 'unchanged').length} file
                {applyPreview.files.filter((f) => f.action !== 'unchanged').length === 1
                  ? ''
                  : 's'}{' '}
                will change in <code className="font-mono text-xs">{applyPreview.root}</code>.
                Overwritten files are backed up first.
              </p>
              <ul className="max-h-48 space-y-1 overflow-y-auto">
                {applyPreview.files.map((file) => (
                  <li key={file.relative_path} className="flex items-center gap-2 text-xs">
                    <span
                      className={`w-16 shrink-0 font-medium ${
                        file.action === 'added'
                          ? 'text-green-700'
                          : file.action === 'changed'
                            ? 'text-amber-700'
                            : 'text-muted-foreground'
                      }`}
                    >
                      {file.action}
                    </span>
                    <span className="truncate font-mono text-foreground">{file.relative_path}</span>
                  </li>
                ))}
              </ul>
              <div className="flex items-center gap-2">
                <button
                  type="button"
                  onClick={handleApplyConfirm}
                  disabled={applying}
                  className="rounded-lg bg-brand-600 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-brand-700 disabled:opacity-50"
                >
                  {applying ? 'Writing…' : 'Write these files'}
                </button>
                <button
                  type="button"
                  onClick={() => setApplyPreview(null)}
                  disabled={applying}
                  className="rounded-lg px-3 py-2 text-sm text-muted-foreground hover:text-foreground"
                >
                  Cancel
                </button>
              </div>
            </div>
          )}

          {applyResult && (
            <p className="flex items-center gap-2 text-sm text-green-700">
              <Check className="h-4 w-4" />
              Wrote {applyResult.written.length} file
              {applyResult.written.length === 1 ? '' : 's'}
              {applyResult.backups.length > 0
                ? `; backed up ${applyResult.backups.length}`
                : ''}
              . Installed, not verified.
            </p>
          )}
        </div>
      )}

      {/* File preview is independent of the chosen method. */}
      <div className="space-y-3">
        <div className="flex items-center gap-3">
          <button
            type="button"
            onClick={handlePreviewFiles}
            disabled={previewLoading}
            className="rounded-lg border border-border px-3 py-1.5 text-sm text-foreground transition-colors hover:bg-accent disabled:opacity-50"
          >
            {previewLoading ? 'Compiling…' : preview ? 'Refresh file preview' : 'Preview files'}
          </button>
          {preview && (
            <span className="text-xs text-muted-foreground">
              {preview.artifact_count} items · {Object.keys(preview.files).length} files
            </span>
          )}
        </div>

        {preview && !warningsDismissed && warnings.length > 0 && (
          <div className="flex items-start gap-3 rounded-xl border border-amber-200 bg-amber-50 p-4">
            <AlertTriangle className="mt-0.5 h-5 w-5 shrink-0 text-amber-600" />
            <div className="min-w-0 flex-1">
              <h3 className="text-sm font-semibold text-amber-800">
                {warnings.length === 1 ? '1 warning' : `${warnings.length} warnings`} — install
                still proceeds
              </h3>
              <ul className="mt-2 space-y-1.5">
                {warnings.map((warning, index) => (
                  <li key={`${warning.code}-${index}`} className="text-sm text-amber-700">
                    {warning.message}
                  </li>
                ))}
              </ul>
            </div>
            <button
              type="button"
              onClick={() => setWarningsDismissed(true)}
              aria-label="Dismiss warnings"
              className="shrink-0 rounded p-1 transition-colors hover:bg-amber-100"
            >
              <X className="h-4 w-4 text-amber-600" />
            </button>
          </div>
        )}

        {preview &&
          Object.keys(preview.files)
            .filter((filename) => permissionFileStatus(filename))
            .map((filename) => (
              <p
                key={filename}
                className="rounded-lg border border-orange-200 bg-orange-50 px-3 py-2 text-xs text-orange-800"
              >
                <span className="font-mono">{filename}</span> — {permissionFileStatus(filename)?.detail}
              </p>
            ))}

        {preview && (
          <ul className="divide-y divide-border overflow-hidden rounded-lg border border-border">
            {Object.keys(preview.files)
              .sort()
              .map((filename) => (
                <li key={filename} className="flex items-center gap-2 px-3 py-2">
                  {filename.includes('/') ? (
                    <Folder className="h-4 w-4 shrink-0 text-muted-foreground" />
                  ) : (
                    <FileIcon className="h-4 w-4 shrink-0 text-muted-foreground" />
                  )}
                  <span className="min-w-0 flex-1 truncate font-mono text-xs text-foreground">
                    {filename}
                  </span>
                  {permissionFileStatus(filename) && (
                    <span className="shrink-0 rounded bg-orange-50 px-1.5 py-0.5 text-xs font-medium text-orange-700">
                      {permissionFileStatus(filename)?.label}
                    </span>
                  )}
                  <button
                    type="button"
                    onClick={() => copyToClipboard(preview.files[filename], filename)}
                    aria-label={`Copy ${filename}`}
                    className="shrink-0 rounded p-1.5 transition-colors hover:bg-accent"
                  >
                    {copied === filename ? (
                      <Check className="h-3.5 w-3.5 text-green-600" />
                    ) : (
                      <Copy className="h-3.5 w-3.5 text-muted-foreground" />
                    )}
                  </button>
                </li>
              ))}
          </ul>
        )}
      </div>
    </div>
  );
}
