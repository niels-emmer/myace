import { useState } from 'react';
import { useMutation } from '@tanstack/react-query';
import {
  ShieldCheck,
  Search,
  Loader2,
  AlertTriangle,
  CircleAlert,
  Info,
} from 'lucide-react';
import { COMPANION_URLS, LocalCompanionSetup, useCompanionHealth } from '../components/LocalCompanionSetup';

interface AuditTarget {
  detected: boolean;
  artifact_count: number;
  artifacts: { artifact_type: string; name: string; file_path?: string }[];
}

interface AuditGap {
  artifact_type: string;
  name: string;
  present_in: string[];
  missing_from: string[];
}

interface AuditDuplicate {
  target: string;
  artifact_type: string;
  name: string;
  count: number;
}

interface AuditResult {
  path: string;
  score: number;
  targets: Record<string, AuditTarget>;
  gaps: AuditGap[];
  duplicates: AuditDuplicate[];
}

const DEFAULT_PATH = '~';

function scoreColor(score: number): string {
  if (score >= 80) return 'text-green-600';
  if (score >= 50) return 'text-amber-600';
  return 'text-destructive';
}

function scoreRingColor(score: number): string {
  if (score >= 80) return 'stroke-green-500';
  if (score >= 50) return 'stroke-amber-500';
  return 'stroke-destructive';
}

export default function SetupAudit() {
  const [rootPath, setRootPath] = useState(DEFAULT_PATH);
  const [result, setResult] = useState<AuditResult | null>(null);

  // Same "is the companion server running" check ImportPage.tsx uses — the
  // browser has no filesystem access, so this page can't audit anything
  // until `myace serve` is reachable on this machine.
  const companionQuery = useCompanionHealth();
  const companionReady = companionQuery.isSuccess;

  const auditMutation = useMutation({
    mutationFn: async () => {
      const res = await fetch(`${COMPANION_URLS[0]}/audit`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-MyACE-Companion': '1' },
        body: JSON.stringify({ path: rootPath }),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: res.statusText }));
        throw new Error(err.detail || 'Audit failed');
      }
      return res.json() as Promise<AuditResult>;
    },
    onSuccess: (data) => setResult(data),
  });

  const detectedTargetNames = result
    ? Object.entries(result.targets)
        .filter(([, t]) => t.detected)
        .map(([name]) => name)
    : [];

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-foreground flex items-center gap-2">
          <ShieldCheck className="h-6 w-6 text-brand-600" />
          Setup Audit
        </h1>
        <p className="text-muted-foreground mt-1">
          Scan your actual local machine for every supported target framework's config, and see
          where they disagree. This is a rough signal, not a certified metric — it compares
          artifact names across each tool's conventional config location, not full content
          fidelity for every format.
        </p>
      </div>

      <div className="bg-card rounded-xl border border-border p-6 space-y-4">
        <div>
          <label className="block text-sm font-medium text-foreground mb-1">
            Directory to audit
          </label>
          <div className="flex gap-2">
            <input
              type="text"
              value={rootPath}
              onChange={(e) => setRootPath(e.target.value)}
              placeholder="~"
              className="flex-1 px-3 py-2 bg-background text-foreground border border-input rounded-lg text-sm font-mono focus:ring-2 focus:ring-brand-500 focus:border-brand-500"
            />
            <button
              onClick={() => auditMutation.mutate()}
              disabled={!companionReady || auditMutation.isPending || !rootPath}
              className="flex items-center gap-2 px-4 py-2 bg-brand-600 text-white rounded-lg hover:bg-brand-700 disabled:opacity-50 text-sm font-medium transition-colors"
            >
              {auditMutation.isPending ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <Search className="h-4 w-4" />
              )}
              Run Audit
            </button>
          </div>
          <p className="text-xs text-muted-foreground mt-2">
            Usually your home directory (<code className="bg-muted px-1 rounded">~</code>), or a
            project root if you keep tool config per-project.
          </p>
          <div className="flex items-center gap-2 mt-2">
            <div
              className={`h-2 w-2 rounded-full ${companionReady ? 'bg-green-400' : 'bg-muted-foreground/30'}`}
            />
            <span className="text-xs text-muted-foreground">
              {companionReady
                ? 'Local scanner detected — ready to audit this machine.'
                : 'Local scanner not detected. See setup steps below.'}
            </span>
          </div>
        </div>

        {auditMutation.isError && (
          <div className="p-3 bg-destructive/10 border border-destructive/30 rounded-lg text-sm text-destructive">
            Audit failed: {auditMutation.error.message}
          </div>
        )}

        {!companionReady && (
          <LocalCompanionSetup sourcePath={rootPath} collectionName="setup-audit" />
        )}
      </div>

      {result && (
        <div className="space-y-6">
          {/* Score */}
          <div className="bg-card rounded-xl border border-border p-6 flex items-center gap-6">
            <ScoreRing score={result.score} />
            <div>
              <p className={`text-3xl font-bold ${scoreColor(result.score)}`}>{result.score}</p>
              <p className="text-sm text-muted-foreground mt-1">
                {detectedTargetNames.length === 0
                  ? 'No supported target framework config detected under this path.'
                  : `${detectedTargetNames.length} target${detectedTargetNames.length === 1 ? '' : 's'} detected: ${detectedTargetNames.join(', ')}`}
              </p>
              <p className="text-xs text-muted-foreground mt-2 flex items-start gap-1.5">
                <Info className="h-3.5 w-3.5 flex-shrink-0 mt-0.5" />
                A rough signal weighted on cross-target coverage parity, duplicate-free naming,
                and non-empty targets — not a certified audit of every tool's real config
                format.
              </p>
            </div>
          </div>

          {/* Gaps */}
          {result.gaps.length > 0 && (
            <div className="bg-card rounded-xl border border-border overflow-hidden">
              <div className="px-6 py-4 border-b border-border flex items-center gap-2">
                <AlertTriangle className="h-4 w-4 text-amber-600" />
                <h2 className="text-lg font-semibold text-card-foreground">
                  Coverage gaps ({result.gaps.length})
                </h2>
              </div>
              <div className="divide-y divide-border">
                {result.gaps.map((gap, i) => (
                  <div key={i} className="px-6 py-3 text-sm">
                    <span className="font-medium text-card-foreground">{gap.name}</span>{' '}
                    <span className="text-xs text-muted-foreground">({gap.artifact_type})</span>
                    <p className="text-muted-foreground mt-0.5">
                      {gap.missing_from.join(', ')} {gap.missing_from.length === 1 ? 'is' : 'are'}{' '}
                      missing {gap.name} that {gap.present_in.join(', ')}{' '}
                      {gap.present_in.length === 1 ? 'has' : 'have'}.
                    </p>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Duplicates */}
          {result.duplicates.length > 0 && (
            <div className="bg-card rounded-xl border border-border overflow-hidden">
              <div className="px-6 py-4 border-b border-border flex items-center gap-2">
                <CircleAlert className="h-4 w-4 text-destructive" />
                <h2 className="text-lg font-semibold text-card-foreground">
                  Duplicate names ({result.duplicates.length})
                </h2>
              </div>
              <div className="divide-y divide-border">
                {result.duplicates.map((dup, i) => (
                  <div key={i} className="px-6 py-3 text-sm">
                    <span className="font-medium text-card-foreground">{dup.name}</span>{' '}
                    <span className="text-xs text-muted-foreground">({dup.artifact_type})</span>
                    <p className="text-muted-foreground mt-0.5">
                      Defined {dup.count} times under {dup.target}.
                    </p>
                  </div>
                ))}
              </div>
            </div>
          )}

          {result.gaps.length === 0 && result.duplicates.length === 0 && detectedTargetNames.length > 0 && (
            <div className="bg-card rounded-xl border border-border p-6 text-sm text-muted-foreground">
              No gaps or duplicates found across detected targets.
            </div>
          )}

          {/* Per-target breakdown */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {Object.entries(result.targets).map(([name, target]) => (
              <div
                key={name}
                className={`bg-card rounded-xl border p-4 ${
                  target.detected ? 'border-border' : 'border-border opacity-50'
                }`}
              >
                <div className="flex items-center justify-between">
                  <span className="text-sm font-medium text-card-foreground">{name}</span>
                  <span className="text-xs text-muted-foreground">
                    {target.detected ? `${target.artifact_count} artifact${target.artifact_count === 1 ? '' : 's'}` : 'not detected'}
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

function ScoreRing({ score }: { score: number }) {
  const radius = 32;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference - (score / 100) * circumference;
  return (
    <svg width="80" height="80" viewBox="0 0 80 80" className="flex-shrink-0">
      <circle cx="40" cy="40" r={radius} className="stroke-muted" strokeWidth="8" fill="none" />
      <circle
        cx="40"
        cy="40"
        r={radius}
        className={scoreRingColor(score)}
        strokeWidth="8"
        fill="none"
        strokeDasharray={circumference}
        strokeDashoffset={offset}
        strokeLinecap="round"
        transform="rotate(-90 40 40)"
      />
    </svg>
  );
}
