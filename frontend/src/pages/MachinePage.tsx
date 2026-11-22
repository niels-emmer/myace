import { Link, useSearchParams } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { Laptop, RefreshCw, ShieldCheck } from 'lucide-react';
import { LocalCompanionSetup, useCompanionHealth } from '../components/LocalCompanionSetup';
import { frameworkLabel } from '../lib/packs';
import SetupAudit from './SetupAudit';
import SyncDashboard from './SyncDashboard';

type Tab = 'overview' | 'audit' | 'sync';

interface OverviewAudit {
  path: string;
  targets: Record<string, { detected: boolean; artifact_count: number }>;
}

const TABS: { id: Tab; label: string }[] = [
  { id: 'overview', label: 'Overview' },
  { id: 'audit', label: 'Audit' },
  { id: 'sync', label: 'Sync' },
];

export default function MachinePage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const tabParam = searchParams.get('tab');
  const tab: Tab = tabParam === 'audit' || tabParam === 'sync' ? tabParam : 'overview';

  const companion = useCompanionHealth();
  const baseUrl = companion.data?.baseUrl;

  const overviewAudit = useQuery({
    queryKey: ['machine-overview-audit', baseUrl],
    queryFn: async () => {
      const res = await fetch(`${baseUrl}/audit`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-MyACE-Companion': '1' },
        body: JSON.stringify({ path: '~' }),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: res.statusText }));
        throw new Error(err.detail || 'Audit failed');
      }
      return res.json() as Promise<OverviewAudit>;
    },
    enabled: Boolean(baseUrl) && tab === 'overview',
    retry: false,
  });

  const setTab = (next: Tab) => {
    const params = new URLSearchParams(searchParams);
    if (next === 'overview') params.delete('tab');
    else params.set('tab', next);
    setSearchParams(params, { replace: true });
  };

  const detectedTargets = overviewAudit.data
    ? Object.entries(overviewAudit.data.targets).filter(([, target]) => target.detected)
    : [];

  return (
    <div className="space-y-6">
      <div>
        <h1 className="flex items-center gap-2 text-2xl font-bold text-foreground">
          <Laptop className="h-6 w-6 text-brand-600" />
          My machine
        </h1>
        <p className="mt-1 text-muted-foreground">
          The local companion, the framework configs it can see, and the installs MyACE knows about.
        </p>
      </div>

      <div className="flex gap-1 border-b border-border" role="tablist" aria-label="Machine sections">
        {TABS.map((item) => (
          <button
            key={item.id}
            role="tab"
            aria-selected={tab === item.id}
            onClick={() => setTab(item.id)}
            className={`-mb-px border-b-2 px-3 py-2 text-sm font-medium transition-colors ${
              tab === item.id
                ? 'border-brand-600 text-brand-700'
                : 'border-transparent text-muted-foreground hover:text-foreground'
            }`}
          >
            {item.label}
          </button>
        ))}
      </div>

      {tab === 'overview' && (
        <div role="tabpanel" aria-label="Overview" className="space-y-6">
          <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
            <div className="rounded-xl border border-border bg-card p-5">
              <div className="flex items-center justify-between gap-2">
                <h2 className="text-sm font-semibold text-card-foreground">Companion</h2>
                <span
                  className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-xs font-medium ${
                    companion.isSuccess
                      ? 'border-green-200 bg-green-50 text-green-700'
                      : companion.isLoading
                        ? 'border-border bg-muted text-muted-foreground'
                        : 'border-amber-200 bg-amber-50 text-amber-700'
                  }`}
                >
                  <span className="h-1.5 w-1.5 rounded-full bg-current" />
                  {companion.isSuccess ? 'Connected' : companion.isLoading ? 'Checking…' : 'Not running'}
                </span>
              </div>
              <p className="mt-2 text-sm text-muted-foreground">
                {companion.isSuccess ? (
                  <>
                    <span className="font-mono text-xs">{baseUrl}</span> · loopback only
                  </>
                ) : (
                  'The companion scans this machine’s filesystem — the browser cannot read it directly.'
                )}
              </p>
              <div className="mt-3 flex flex-wrap gap-2">
                <button
                  onClick={() => setTab('audit')}
                  className="inline-flex items-center gap-2 rounded-lg bg-brand-600 px-3 py-1.5 text-sm font-medium text-white transition-colors hover:bg-brand-700"
                >
                  <ShieldCheck className="h-4 w-4" />
                  Run setup audit
                </button>
                <button
                  onClick={() => {
                    companion.refetch();
                    overviewAudit.refetch();
                  }}
                  className="inline-flex items-center gap-2 rounded-lg border border-border bg-card px-3 py-1.5 text-sm font-medium transition-colors hover:bg-accent"
                >
                  <RefreshCw className="h-4 w-4" />
                  Reconnect
                </button>
              </div>
            </div>

            <div className="rounded-xl border border-border bg-card p-5">
              <h2 className="text-sm font-semibold text-card-foreground">Install &amp; drift</h2>
              <p className="mt-2 text-sm text-muted-foreground">
                Per-framework install status is reported by{' '}
                <code className="rounded bg-muted px-1 py-0.5 text-xs">myace check --report</code>{' '}
                from your machines.
              </p>
              <Link
                to="/machine?tab=sync"
                className="mt-3 inline-flex items-center gap-2 text-sm font-medium text-brand-600 hover:underline"
              >
                Open sync report
              </Link>
            </div>
          </div>

          {!companion.isSuccess && !companion.isLoading && (
            <LocalCompanionSetup sourcePath="~" collectionName="machine-overview" />
          )}

          <div className="overflow-hidden rounded-xl border border-border bg-card">
            <div className="flex items-center justify-between border-b border-border px-5 py-4">
              <h2 className="text-sm font-semibold text-card-foreground">Detected frameworks</h2>
              {detectedTargets.length > 0 && (
                <span className="text-xs text-muted-foreground">
                  {detectedTargets.length} detected under {overviewAudit.data?.path ?? '~'}
                </span>
              )}
            </div>
            {overviewAudit.isLoading ? (
              <p className="px-5 py-6 text-sm text-muted-foreground">Scanning ~ for framework configs…</p>
            ) : overviewAudit.isError ? (
              <p className="px-5 py-6 text-sm text-destructive">
                Could not scan this machine: {(overviewAudit.error as Error).message}
              </p>
            ) : detectedTargets.length > 0 ? (
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-border bg-muted/50 text-left text-muted-foreground">
                    <th className="px-5 py-2.5 font-medium">Framework</th>
                    <th className="px-5 py-2.5 font-medium">Items found</th>
                    <th className="px-5 py-2.5 font-medium">Status</th>
                  </tr>
                </thead>
                <tbody>
                  {detectedTargets.map(([name, target]) => (
                    <tr key={name} className="border-b border-border/50 last:border-0">
                      <td className="px-5 py-3 font-medium text-card-foreground">{frameworkLabel(name)}</td>
                      <td className="px-5 py-3 text-muted-foreground">{target.artifact_count}</td>
                      <td className="px-5 py-3">
                        <span className="rounded border border-green-200 bg-green-50 px-2 py-0.5 text-xs text-green-700">
                          detected
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            ) : (
              <p className="px-5 py-6 text-sm text-muted-foreground">
                {companion.isSuccess
                  ? 'No supported framework configs found under your home directory.'
                  : 'Connect the companion to detect framework configs on this machine.'}
              </p>
            )}
          </div>
        </div>
      )}

      {tab === 'audit' && (
        <div role="tabpanel" aria-label="Audit">
          <SetupAudit embedded />
        </div>
      )}

      {tab === 'sync' && (
        <div role="tabpanel" aria-label="Sync">
          <SyncDashboard embedded />
        </div>
      )}
    </div>
  );
}
