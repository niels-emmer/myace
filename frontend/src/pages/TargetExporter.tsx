import { useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { Download, Copy, Terminal, Check, AlertTriangle, X } from 'lucide-react';
import { profilesApi, adaptersApi } from '../lib/api';
import type { CompileResult } from '../types';

export default function TargetExporter() {
  const [searchParams] = useSearchParams();
  const [selectedProfile, setSelectedProfile] = useState(searchParams.get('profile') ?? '');
  const [selectedTarget, setSelectedTarget] = useState('opencode');
  const [result, setResult] = useState<CompileResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [copied, setCopied] = useState<string | null>(null);
  const [warningsDismissed, setWarningsDismissed] = useState(false);

  const { data: profiles } = useQuery({
    queryKey: ['profiles'],
    queryFn: () => profilesApi.list(),
  });

  const { data: adapters } = useQuery({
    queryKey: ['adapters'],
    queryFn: () => adaptersApi.list(),
  });

  const [downloading, setDownloading] = useState(false);
  const [downloadError, setDownloadError] = useState<string | null>(null);

  const handleCompile = async () => {
    if (!selectedProfile) return;
    setLoading(true);
    try {
      const res = await profilesApi.compile({
        profile_id: selectedProfile,
        target: selectedTarget,
      });
      setResult(res);
      // A fresh compile can carry its own new warnings (or resolve old
      // ones) — don't let a dismissal from a previous result carry over.
      setWarningsDismissed(false);
    } catch (err) {
      console.error('Compilation failed:', err);
    }
    setLoading(false);
  };

  const handleDownloadZip = async () => {
    if (!result) return;
    setDownloading(true);
    setDownloadError(null);
    try {
      // Use result.profile_id/target — the values that actually produced the
      // displayed preview — not the live dropdown state. The dropdowns can
      // change after Compile is clicked (e.g. comparing targets) without
      // triggering a recompile, and the zip must match what's on screen.
      const res = await fetch('/api/v1/profiles/compile/zip', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'same-origin',
        body: JSON.stringify({ profile_id: result.profile_id, target: result.target }),
      });
      if (!res.ok) {
        throw new Error(`Download failed (${res.status})`);
      }
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `${result.profile_name}-${result.target}.zip`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      // Revoking synchronously right after click() races Safari's native
      // "Save As" dialog: WebKit defers reading the blob until the user
      // responds, and an immediately-revoked object URL can make that read
      // fail or save a truncated/empty file. Give the browser a tick to
      // start consuming the blob before invalidating the URL.
      setTimeout(() => URL.revokeObjectURL(url), 1000);
    } catch (err) {
      console.error('Zip download failed:', err);
      setDownloadError('Could not download the zip. Try again.');
    }
    setDownloading(false);
  };

  const copyToClipboard = async (text: string, key: string) => {
    await navigator.clipboard.writeText(text);
    setCopied(key);
    setTimeout(() => setCopied(null), 2000);
  };

  const cliCommand = result
    ? `myace pull --profile ${result.profile_name} --target ${result.target}`
    : '';

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-foreground">Compile Profile</h1>
        <p className="text-muted-foreground mt-1">
          Turn a profile into the config files a target framework expects (CLAUDE.md, AGENTS.md, etc.) — copy them out or pull with the CLI.
        </p>
      </div>

      {/* Controls */}
      <div className="bg-card rounded-xl border border-border p-6">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-4">
          <div>
            <label className="block text-sm font-medium text-foreground mb-1">Profile</label>
            <select
              value={selectedProfile}
              onChange={(e) => setSelectedProfile(e.target.value)}
              className="w-full px-3 py-2 bg-background text-foreground border border-input rounded-lg text-sm"
            >
              <option value="">Select a profile...</option>
              {profiles?.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.name}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-foreground mb-1">Target Framework</label>
            <select
              value={selectedTarget}
              onChange={(e) => setSelectedTarget(e.target.value)}
              className="w-full px-3 py-2 bg-background text-foreground border border-input rounded-lg text-sm"
            >
              {adapters?.filter((a) => a.enabled).map((a) => (
                <option key={a.name} value={a.name}>
                  {a.name}
                </option>
              ))}
            </select>
          </div>
          <div className="flex items-end">
            <button
              onClick={handleCompile}
              disabled={!selectedProfile || loading}
              className="flex items-center gap-2 px-4 py-2 bg-brand-600 text-white rounded-lg hover:bg-brand-700 disabled:opacity-50 text-sm font-medium"
            >
              <Download className="h-4 w-4" />
              {loading ? 'Compiling...' : 'Compile'}
            </button>
          </div>
        </div>

        {/* CLI Command */}
        {cliCommand && (
          <div className="bg-muted rounded-lg p-3 flex items-center justify-between mb-3">
            <div className="flex items-center gap-2">
              <Terminal className="h-4 w-4 text-muted-foreground" />
              <code className="text-sm text-foreground">{cliCommand}</code>
            </div>
            <button
              onClick={() => copyToClipboard(cliCommand, 'cli')}
              className="p-1.5 hover:bg-accent rounded transition-colors"
            >
              {copied === 'cli' ? (
                <Check className="h-4 w-4 text-green-600" />
              ) : (
                <Copy className="h-4 w-4 text-muted-foreground" />
              )}
            </button>
          </div>
        )}

        {/* Browser-only download, no CLI required */}
        {result && (
          <div className="flex items-center gap-3">
            <button
              onClick={handleDownloadZip}
              disabled={downloading}
              className="flex items-center gap-2 px-3 py-1.5 border border-border rounded-lg hover:bg-accent disabled:opacity-50 text-sm font-medium text-foreground"
            >
              <Download className="h-4 w-4" />
              {downloading ? 'Preparing zip...' : 'Download as .zip'}
            </button>
            {downloadError && (
              <span className="text-sm text-destructive">{downloadError}</span>
            )}
          </div>
        )}
      </div>

      {/* Results */}
      {result && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-lg font-semibold text-foreground">
              Output — {result.artifact_count} artifacts, {Object.keys(result.files).length} files
            </h2>
          </div>

          {/* Compile-time validation warnings — advisory (amber), not errors (red).
              The compiled output above is still valid; these just flag something
              worth a human look, e.g. an artifact name collision across composed
              collections. */}
          {!warningsDismissed && result.warnings && result.warnings.length > 0 && (
            <div className="bg-amber-50 border border-amber-200 rounded-xl p-4 flex items-start gap-3">
              <AlertTriangle className="h-5 w-5 text-amber-600 flex-shrink-0 mt-0.5" />
              <div className="flex-1 min-w-0">
                <h3 className="text-sm font-semibold text-amber-800">
                  {result.warnings.length === 1
                    ? '1 warning from compilation'
                    : `${result.warnings.length} warnings from compilation`}
                </h3>
                <ul className="mt-2 space-y-1.5">
                  {result.warnings.map((warning, index) => (
                    <li key={index} className="text-sm text-amber-700">
                      {warning.message}
                    </li>
                  ))}
                </ul>
              </div>
              <button
                onClick={() => setWarningsDismissed(true)}
                aria-label="Dismiss warnings"
                className="p-1 hover:bg-amber-100 rounded transition-colors flex-shrink-0"
              >
                <X className="h-4 w-4 text-amber-600" />
              </button>
            </div>
          )}

          {Object.entries(result.files).map(([filename, content]) => (
            <div key={filename} className="bg-card rounded-xl border border-border overflow-hidden">
              <div className="flex items-center justify-between px-4 py-2 bg-muted border-b border-border">
                <span className="text-sm font-mono text-foreground">{filename}</span>
                <button
                  onClick={() => copyToClipboard(content, filename)}
                  className="p-1.5 hover:bg-accent rounded transition-colors"
                >
                  {copied === filename ? (
                    <Check className="h-4 w-4 text-green-600" />
                  ) : (
                    <Copy className="h-4 w-4 text-muted-foreground" />
                  )}
                </button>
              </div>
              <pre className="p-4 text-xs text-muted-foreground overflow-x-auto max-h-64 overflow-y-auto">
                {content}
              </pre>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
