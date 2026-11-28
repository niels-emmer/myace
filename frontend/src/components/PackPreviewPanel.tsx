import { useEffect, useMemo, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { AlertTriangle, Check, Copy, Download, Loader2, Terminal } from 'lucide-react';
import { packApi } from '../lib/packApi';
import { probeMcpAvailability } from '../lib/mcp';
import { frameworkLabel } from '../lib/packs';

/**
 * "Preview install" tab for a public pack page (docs/plans/public-compiled-preview.md).
 *
 * Shows what the pack compiles to for one framework, by calling the anonymous
 * `install.md?format=json` route. Read-only by design (ADR-0018): nothing is
 * written anywhere and a preview never counts as a use. File text is pack
 * content and therefore untrusted (rule 43), so it is only ever rendered as
 * plain text inside a `<pre>`.
 *
 * Mounted only while its tab is open, so the compile is not paid for by anyone
 * who never looks.
 */
const DEFAULT_TARGET = 'claude-code';

function useCopy(): [string | null, (key: string, text: string) => void] {
  const [copied, setCopied] = useState<string | null>(null);
  useEffect(() => {
    if (!copied) return undefined;
    const timer = window.setTimeout(() => setCopied(null), 1500);
    return () => window.clearTimeout(timer);
  }, [copied]);
  const copy = (key: string, text: string) => {
    void navigator.clipboard
      ?.writeText(text)
      .then(() => setCopied(key))
      .catch(() => {});
  };
  return [copied, copy];
}

export default function PackPreviewPanel({ packId }: { packId: string }) {
  const origin = window.location.origin;
  const [target, setTarget] = useState<string | null>(null);
  const [selectedPath, setSelectedPath] = useState<string | null>(null);
  const [copied, copy] = useCopy();

  const { data: frameworks } = useQuery({
    queryKey: ['frameworks'],
    queryFn: () => packApi.getFrameworks(),
    staleTime: 5 * 60 * 1000,
  });

  const { data: mcpAvailable } = useQuery({
    queryKey: ['mcp-available'],
    queryFn: probeMcpAvailability,
    staleTime: Infinity,
  });

  const activeTarget =
    target ?? (frameworks?.includes(DEFAULT_TARGET) ? DEFAULT_TARGET : frameworks?.[0] ?? null);

  const {
    data: preview,
    isLoading,
    error,
  } = useQuery({
    queryKey: ['pack-preview', packId, activeTarget],
    queryFn: () => packApi.previewInstall(packId, activeTarget!),
    enabled: !!activeTarget,
    // Output is a pure function of pack and target; no need to refetch on focus.
    staleTime: 5 * 60 * 1000,
    refetchOnWindowFocus: false,
    retry: false,
  });

  const paths = useMemo(() => Object.keys(preview?.files ?? {}).sort(), [preview]);
  // Open on the top-level file (CLAUDE.md, AGENTS.md) when there is one: it is
  // the rules file, which is what most people want to see first.
  const defaultPath = paths.find((path) => !path.includes('/')) ?? paths[0] ?? null;
  const currentPath = selectedPath && paths.includes(selectedPath) ? selectedPath : defaultPath;
  const content = currentPath ? preview?.files[currentPath] ?? '' : '';

  const installUrl = activeTarget
    ? `${origin}/api/v1/collections/community/${packId}/install.md?target=${encodeURIComponent(activeTarget)}`
    : null;
  const zipUrl = installUrl ? `${installUrl}&format=zip` : null;
  const mcpCommand = `claude mcp add --transport http myace ${origin}/mcp`;

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-end gap-3">
        <div>
          <label htmlFor="preview-target" className="text-xs font-medium text-muted-foreground">
            Framework
          </label>
          <select
            id="preview-target"
            value={activeTarget ?? ''}
            onChange={(event) => {
              setTarget(event.target.value);
              setSelectedPath(null);
            }}
            disabled={!frameworks}
            className="mt-1 block rounded-lg border border-input bg-background px-3 py-2 text-sm text-foreground"
          >
            {(frameworks ?? []).map((name) => (
              <option key={name} value={name}>
                {frameworkLabel(name)}
              </option>
            ))}
          </select>
        </div>
        {zipUrl && (
          <a
            href={zipUrl}
            download
            className="inline-flex items-center gap-2 rounded-lg border border-border px-3 py-2 text-sm text-foreground transition-colors hover:bg-accent"
          >
            <Download className="h-4 w-4" aria-hidden="true" />
            Download zip
          </a>
        )}
        <p className="text-xs text-muted-foreground sm:ml-auto">
          Read-only preview. Nothing is installed and it does not count as a use.
        </p>
      </div>

      {isLoading && (
        <p role="status" className="flex items-center gap-2 text-sm text-muted-foreground">
          <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />
          Compiling preview…
        </p>
      )}

      {error && (
        <p role="alert" className="rounded-lg border border-destructive/30 bg-destructive/5 p-3 text-sm text-destructive">
          {(error as Error).message}
        </p>
      )}

      {preview && preview.warnings.length > 0 && (
        <div role="note" className="rounded-lg border border-amber-300 bg-amber-50 p-3 text-sm text-amber-900">
          <p className="flex items-center gap-2 font-medium">
            <AlertTriangle className="h-4 w-4" aria-hidden="true" />
            {preview.warnings.length} compile {preview.warnings.length === 1 ? 'warning' : 'warnings'}
          </p>
          <ul className="mt-1 list-disc pl-6">
            {preview.warnings.map((warning, index) => (
              <li key={`${warning.code}-${index}`}>{warning.message}</li>
            ))}
          </ul>
        </div>
      )}

      {preview && paths.length > 0 && (
        <div className="grid gap-3 md:grid-cols-[minmax(0,16rem)_minmax(0,1fr)]">
          <nav aria-label="Compiled files">
            <ul className="max-h-96 space-y-0.5 overflow-auto rounded-lg border border-border bg-card p-1">
              {paths.map((path) => (
                <li key={path}>
                  <button
                    type="button"
                    onClick={() => setSelectedPath(path)}
                    aria-current={path === currentPath ? 'true' : undefined}
                    className={`block w-full truncate rounded px-2 py-1.5 text-left text-xs transition-colors ${
                      path === currentPath
                        ? 'bg-brand-50 font-medium text-brand-700'
                        : 'text-muted-foreground hover:bg-accent hover:text-foreground'
                    }`}
                    title={path}
                  >
                    {path}
                  </button>
                </li>
              ))}
            </ul>
            <p className="mt-1 text-xs text-muted-foreground">
              {paths.length} {paths.length === 1 ? 'file' : 'files'}
            </p>
          </nav>
          <div className="min-w-0 rounded-lg border border-border bg-card">
            <div className="flex items-center justify-between gap-2 border-b border-border px-3 py-2">
              <span className="min-w-0 truncate text-xs font-medium text-foreground">{currentPath}</span>
              <button
                type="button"
                onClick={() => copy('file', content)}
                className="inline-flex shrink-0 items-center gap-1 rounded px-2 py-1 text-xs text-muted-foreground hover:text-foreground"
              >
                {copied === 'file' ? <Check className="h-3.5 w-3.5" /> : <Copy className="h-3.5 w-3.5" />}
                {copied === 'file' ? 'Copied' : 'Copy'}
              </button>
            </div>
            {/* Plain text only: pack content is untrusted. */}
            <pre
              tabIndex={0}
              aria-label={currentPath ? `Contents of ${currentPath}` : 'File contents'}
              className="max-h-96 overflow-auto whitespace-pre-wrap break-words p-3 text-xs text-foreground"
            >
              {content}
            </pre>
          </div>
        </div>
      )}

      <section aria-labelledby="agent-install-heading" className="space-y-2 rounded-lg border border-border bg-card p-4">
        <h2 id="agent-install-heading" className="flex items-center gap-2 text-sm font-semibold text-foreground">
          <Terminal className="h-4 w-4" aria-hidden="true" />
          Install with a coding agent
        </h2>
        <p className="text-xs text-muted-foreground">
          Give your agent this pack&rsquo;s install URL. It reads the compiled files and proposes the
          install; you approve every file it writes.
        </p>
        {installUrl && <CopyRow label="Install URL" value={installUrl} copied={copied} copy={copy} />}
        {mcpAvailable && (
          <CopyRow label="Or connect the MCP server (Claude Code)" value={mcpCommand} copied={copied} copy={copy} />
        )}
      </section>
    </div>
  );
}

function CopyRow({
  label,
  value,
  copied,
  copy,
}: {
  label: string;
  value: string;
  copied: string | null;
  copy: (key: string, text: string) => void;
}) {
  return (
    <div>
      <p className="text-xs font-medium text-muted-foreground">{label}</p>
      <div className="mt-1 flex items-center gap-2">
        <code className="min-w-0 flex-1 overflow-x-auto whitespace-nowrap rounded border border-border bg-muted px-2 py-1.5 text-xs text-foreground">
          {value}
        </code>
        <button
          type="button"
          onClick={() => copy(label, value)}
          aria-label={`Copy ${label}`}
          className="inline-flex shrink-0 items-center gap-1 rounded border border-border px-2 py-1.5 text-xs text-foreground hover:bg-accent"
        >
          {copied === label ? <Check className="h-3.5 w-3.5" /> : <Copy className="h-3.5 w-3.5" />}
          {copied === label ? 'Copied' : 'Copy'}
        </button>
      </div>
    </div>
  );
}
