import { useMemo, useState } from 'react';
import { Link, useParams, useSearchParams } from 'react-router-dom';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { ArrowLeft, Download } from 'lucide-react';
import { profilesApi } from '../lib/api';
import { installsApi } from '../lib/setupApi';
import { profileTargets, resolveInstallPath, supportsMachineInstall } from '../types/setup';
import type { InstallLocation } from '../types/setup';
import InstallMethodPanel from '../components/InstallMethodPanel';

export default function TargetExporter() {
  const { id } = useParams<{ id: string }>();
  const [searchParams] = useSearchParams();
  const queryClient = useQueryClient();

  const { data: profile, isLoading: loadingProfile } = useQuery({
    queryKey: ['profile', id],
    queryFn: () => profilesApi.get(id!),
    enabled: !!id,
  });

  const { data: claims } = useQuery({
    queryKey: ['installs', id],
    queryFn: () => installsApi.list(id!),
    enabled: !!id,
  });

  const targets = useMemo(() => (profile ? profileTargets(profile) : []), [profile]);
  const requestedTarget = searchParams.get('target');
  const [targetOverride, setTargetOverride] = useState<string | null>(null);
  const [locationOverride, setLocationOverride] = useState<InstallLocation | null>(null);

  // Derived, not stored in an effect: the requested target wins when it is
  // one of the setup's frameworks, otherwise the first configured framework.
  const selectedTarget =
    targetOverride ??
    (requestedTarget && (targets.length === 0 || targets.includes(requestedTarget))
      ? requestedTarget
      : (targets[0] ?? ''));

  const claimForTarget = claims?.find((claim) => claim.target === selectedTarget);
  const location: InstallLocation =
    locationOverride ??
    claimForTarget?.location ??
    (supportsMachineInstall(selectedTarget) ? 'machine' : 'project');

  if (loadingProfile) {
    return <div className="py-12 text-center text-muted-foreground">Loading setup…</div>;
  }

  if (!profile) {
    return <div className="py-12 text-center text-muted-foreground">Setup not found.</div>;
  }

  const machineSupported = supportsMachineInstall(selectedTarget);

  return (
    <div className="space-y-6">
      <div>
        <Link
          to={`/setups/${profile.id}`}
          className="inline-flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground"
        >
          <ArrowLeft className="h-4 w-4" />
          {profile.name}
        </Link>
        <h1 className="mt-2 text-2xl font-bold text-foreground">Install “{profile.name}”</h1>
        <p className="mt-1 text-muted-foreground">
          Choose a framework and where its files should go. Nothing is written until you confirm.
        </p>
      </div>

      <div className="bg-card rounded-xl border border-border p-6 space-y-5">
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
          <div>
            <label htmlFor="install-target" className="mb-1 block text-sm font-medium text-foreground">
              Framework
            </label>
            <select
              id="install-target"
              value={selectedTarget}
              onChange={(event) => {
                setTargetOverride(event.target.value);
                setLocationOverride(null);
              }}
              className="w-full rounded-lg border border-input bg-background px-3 py-2 text-sm text-foreground"
            >
              {targets.length === 0 && <option value="">No frameworks configured</option>}
              {targets.map((target) => (
                <option key={target} value={target}>
                  {target} — {resolveInstallPath(target, 'machine')}
                </option>
              ))}
            </select>
          </div>

          <div>
            <span className="mb-1 block text-sm font-medium text-foreground">Location</span>
            <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
              <button
                type="button"
                onClick={() => setLocationOverride('project')}
                className={`rounded-lg border px-3 py-2 text-left text-sm transition-colors ${
                  location === 'project'
                    ? 'border-brand-500 bg-brand-50 text-brand-700'
                    : 'border-border text-muted-foreground hover:border-input'
                }`}
              >
                <span className="block font-medium">This project</span>
                <span className="block font-mono text-xs">
                  {resolveInstallPath(selectedTarget, 'project')}
                </span>
              </button>
              <button
                type="button"
                onClick={() => setLocationOverride('machine')}
                disabled={!machineSupported}
                title={
                  machineSupported
                    ? undefined
                    : 'This framework’s output is project-only — it has no machine-wide root'
                }
                className={`rounded-lg border px-3 py-2 text-left text-sm transition-colors ${
                  location === 'machine'
                    ? 'border-brand-500 bg-brand-50 text-brand-700'
                    : 'border-border text-muted-foreground hover:border-input'
                } disabled:cursor-not-allowed disabled:opacity-50`}
              >
                <span className="block font-medium">This machine</span>
                <span className="block font-mono text-xs">
                  {resolveInstallPath(selectedTarget, 'machine')}
                </span>
              </button>
            </div>
          </div>
        </div>

        {selectedTarget && targets.length > 0 && (
          <InstallMethodPanel
            key={`${selectedTarget}:${location}`}
            profileId={profile.id}
            profileName={profile.name}
            target={selectedTarget}
            location={location}
            onClaimed={() => {
              queryClient.invalidateQueries({ queryKey: ['installs', profile.id] });
            }}
          />
        )}

        {targets.length === 0 && (
          <p className="flex items-center gap-2 text-sm text-muted-foreground">
            <Download className="h-4 w-4" />
            This setup has no frameworks yet. Edit it to add one before installing.
          </p>
        )}
      </div>
    </div>
  );
}
