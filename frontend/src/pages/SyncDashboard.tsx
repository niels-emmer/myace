import { useQuery } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import { RefreshCw, CheckCircle2, AlertTriangle, ExternalLink } from 'lucide-react';
import { syncApi } from '../lib/api';
import type { SyncStatus } from '../types';

function formatDate(value: string): string {
  return new Date(value).toLocaleString();
}

function StatusBadge({ status }: { status: SyncStatus }) {
  if (status.in_sync) {
    return (
      <span className="inline-flex items-center gap-1.5 px-2.5 py-1 bg-green-50 text-green-700 border border-green-200 rounded-full text-xs font-medium">
        <CheckCircle2 className="h-3.5 w-3.5" />
        In sync
      </span>
    );
  }
  if (status.locally_modified_files.length > 0) {
    return (
      <span className="inline-flex items-center gap-1.5 px-2.5 py-1 bg-amber-50 text-amber-700 border border-amber-200 rounded-full text-xs font-medium">
        <AlertTriangle className="h-3.5 w-3.5" />
        Locally modified
      </span>
    );
  }
  return (
    <span className="inline-flex items-center gap-1.5 px-2.5 py-1 bg-blue-50 text-blue-700 border border-blue-200 rounded-full text-xs font-medium">
      <RefreshCw className="h-3.5 w-3.5" />
      Stale
    </span>
  );
}

function Hint({ status }: { status: SyncStatus }) {
  if (status.in_sync) return <span className="text-muted-foreground">—</span>;
  if (status.locally_modified_files.length > 0) {
    return (
      <span className="text-muted-foreground">
        Review your local edits to{' '}
        <span className="font-mono text-xs">
          {status.locally_modified_files.slice(0, 3).join(', ')}
          {status.locally_modified_files.length > 3
            ? ` (+${status.locally_modified_files.length - 3} more)`
            : ''}
        </span>
      </span>
    );
  }
  return (
    <span className="text-muted-foreground">
      Run <code className="font-mono text-xs bg-muted px-1 py-0.5 rounded">myace pull</code> to
      update
    </span>
  );
}

export default function SyncDashboard() {
  const { data: statuses, isLoading, isError, error } = useQuery({
    queryKey: ['sync-status'],
    queryFn: () => syncApi.getStatus(),
  });

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-foreground flex items-center gap-2">
          <RefreshCw className="h-6 w-6 text-muted-foreground" />
          Sync Dashboard
        </h1>
        <p className="text-muted-foreground mt-1">
          Drift status reported by <code className="font-mono text-xs bg-muted px-1 py-0.5 rounded">myace check --report</code>{' '}
          or <code className="font-mono text-xs bg-muted px-1 py-0.5 rounded">myace watch --report</code> from
          your own machines. Nothing appears here unless you opt in with{' '}
          <code className="font-mono text-xs bg-muted px-1 py-0.5 rounded">--report</code> — this
          page only ever shows your own reports, never anyone else's.
        </p>
      </div>

      {isLoading ? (
        <p className="text-sm text-muted-foreground">Loading sync status...</p>
      ) : isError ? (
        <p className="text-sm text-destructive">{(error as Error).message}</p>
      ) : statuses && statuses.length > 0 ? (
        <div className="bg-card border border-border rounded-xl overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-border bg-muted/50">
                  <th className="text-left py-3 px-4 font-medium text-muted-foreground">Profile</th>
                  <th className="text-left py-3 px-4 font-medium text-muted-foreground">Target</th>
                  <th className="text-left py-3 px-4 font-medium text-muted-foreground">Machine</th>
                  <th className="text-left py-3 px-4 font-medium text-muted-foreground">Status</th>
                  <th className="text-left py-3 px-4 font-medium text-muted-foreground">Hint</th>
                  <th className="text-left py-3 px-4 font-medium text-muted-foreground">Last checked</th>
                </tr>
              </thead>
              <tbody>
                {statuses.map((s) => (
                  <tr key={s.id} className="border-b border-border/50 last:border-0">
                    <td className="py-3 px-4 text-card-foreground font-medium">
                      <Link
                        to={`/profiles/${s.profile_id}`}
                        className="hover:text-brand-600 inline-flex items-center gap-1"
                      >
                        {s.profile_name}
                        <ExternalLink className="h-3 w-3 text-muted-foreground" />
                      </Link>
                    </td>
                    <td className="py-3 px-4 text-muted-foreground font-mono text-xs">{s.target}</td>
                    <td className="py-3 px-4 text-muted-foreground">{s.machine_label}</td>
                    <td className="py-3 px-4">
                      <StatusBadge status={s} />
                    </td>
                    <td className="py-3 px-4">
                      <Hint status={s} />
                    </td>
                    <td className="py-3 px-4 text-muted-foreground">{formatDate(s.last_checked_at)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      ) : (
        <p className="text-sm text-muted-foreground">
          Nothing reported yet. Run{' '}
          <code className="font-mono text-xs bg-muted px-1 py-0.5 rounded">myace check --report</code>{' '}
          from a machine you've pulled a profile onto to see it here.
        </p>
      )}
    </div>
  );
}
