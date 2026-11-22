import { useQuery } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import {
  AlertTriangle,
  ArrowRight,
  CheckCircle2,
  Download,
  FolderGit2,
  Plus,
  Sparkles,
  Star,
} from 'lucide-react';
import { adaptersApi, collectionsApi, profilesApi, syncApi } from '../lib/api';
import { BUNDLES } from '../lib/bundles';
import { packSourceLabel, packSource } from '../lib/packs';
import type { Profile, SyncStatus } from '../types';

type InstallState = 'verified' | 'changed' | 'not-verified' | 'not-installed';

const INSTALL_STATE_LABELS: Record<InstallState, string> = {
  verified: 'verified',
  changed: 'changed',
  'not-verified': 'not verified',
  'not-installed': 'not installed',
};

const INSTALL_STATE_CLASSES: Record<InstallState, string> = {
  verified: 'bg-green-50 text-green-700 border-green-200',
  changed: 'bg-amber-50 text-amber-700 border-amber-200',
  'not-verified': 'bg-blue-50 text-blue-700 border-blue-200',
  'not-installed': 'bg-muted text-muted-foreground border-border',
};

function installState(row?: SyncStatus): InstallState {
  if (!row) return 'not-installed';
  if (row.locally_modified_files.length > 0) return 'changed';
  if (!row.in_sync) return 'not-verified';
  return 'verified';
}

function profileTargets(profile: Profile): string[] {
  if (profile.target_frameworks && profile.target_frameworks.length > 0) {
    return profile.target_frameworks;
  }
  return profile.target_framework ? [profile.target_framework] : [];
}

function driftCount(rows: SyncStatus[]): number {
  const files = rows.reduce((total, row) => total + row.locally_modified_files.length, 0);
  return files > 0 ? files : rows.length;
}

export default function Home() {
  const { data: profiles } = useQuery({
    queryKey: ['profiles'],
    queryFn: () => profilesApi.list(),
  });
  const { data: syncStatuses } = useQuery({
    queryKey: ['sync-status'],
    queryFn: () => syncApi.getStatus(),
  });
  const { data: collections } = useQuery({
    queryKey: ['collections'],
    queryFn: () => collectionsApi.list(),
  });
  const { data: adapters } = useQuery({
    queryKey: ['adapters'],
    queryFn: () => adaptersApi.list(),
  });
  const { data: community } = useQuery({
    queryKey: ['community-collections', { limit: 4, sort: 'rating' }],
    queryFn: () => collectionsApi.listCommunity({ limit: 4, sort: 'rating' }),
  });

  const setups = profiles ?? [];
  const syncRows = syncStatuses ?? [];
  const driftRows = syncRows.filter(
    (row) => !row.in_sync || row.locally_modified_files.length > 0,
  );
  const appVersion: string = import.meta.env.VITE_APP_VERSION ?? 'dev';
  const frameworkCount = adapters?.length ?? 12;

  const collectionById = new Map((collections ?? []).map((collection) => [collection.id, collection]));
  const packNamesFor = (profile: Profile): string[] =>
    [profile.base_collection_id, ...profile.additional_collection_ids]
      .map((id) => collectionById.get(id)?.name)
      .filter((name): name is string => Boolean(name));

  const basePacks = (collections ?? []).filter((collection) => collection.collection_type === 'base');
  const communityHighlights = (community?.items ?? [])
    .filter((collection) => !collection.is_starter_pack)
    .slice(0, 4);

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-bold text-foreground">Home</h1>
        <p className="text-muted-foreground mt-1">
          Your setups, their framework status, and what to do next.
        </p>
      </div>

      {/* One state, derived from setups + sync reports. */}
      {profiles && syncStatuses && (
        <>
          {setups.length === 0 && (
            <div className="flex flex-col gap-4 rounded-xl border border-brand-200 bg-brand-50 p-6 sm:flex-row sm:items-center">
              <div className="flex h-11 w-11 flex-shrink-0 items-center justify-center rounded-lg bg-brand-100 text-brand-700">
                <Sparkles className="h-5 w-5" />
              </div>
              <div className="flex-1">
                <h2 className="font-semibold text-brand-900">Build your first setup</h2>
                <p className="mt-1 text-sm text-brand-800">
                  Pick the frameworks you use, choose a pack, and install. About two minutes.
                </p>
              </div>
              <Link
                to="/setups"
                className="inline-flex items-center justify-center gap-2 rounded-lg bg-brand-600 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-brand-700"
              >
                Start setup
                <ArrowRight className="h-4 w-4" />
              </Link>
            </div>
          )}

          {setups.length > 0 && syncRows.length === 0 && (
            <div className="flex flex-col gap-4 rounded-xl border border-brand-200 bg-brand-50 p-6 sm:flex-row sm:items-center">
              <div className="flex h-11 w-11 flex-shrink-0 items-center justify-center rounded-lg bg-brand-100 text-brand-700">
                <Download className="h-5 w-5" />
              </div>
              <div className="flex-1">
                <h2 className="font-semibold text-brand-900">Your setup is ready — install it</h2>
                <p className="mt-1 text-sm text-brand-800">
                  {setups[0].name} has not been written to a framework yet.
                </p>
              </div>
              <Link
                to={`/setups/${setups[0].id}/install`}
                className="inline-flex items-center justify-center gap-2 rounded-lg bg-brand-600 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-brand-700"
              >
                Install now
                <ArrowRight className="h-4 w-4" />
              </Link>
            </div>
          )}

          {setups.length > 0 && syncRows.length > 0 && driftRows.length > 0 && (
            <div className="flex flex-col gap-4 rounded-xl border border-amber-200 bg-amber-50 p-6 sm:flex-row sm:items-center">
              <div className="flex h-11 w-11 flex-shrink-0 items-center justify-center rounded-lg bg-amber-100 text-amber-700">
                <AlertTriangle className="h-5 w-5" />
              </div>
              <div className="flex-1">
                <h2 className="font-semibold text-amber-900">
                  {driftRows[0].profile_name}: {driftCount(driftRows)}{' '}
                  {driftCount(driftRows) === 1 ? 'change' : 'changes'} since install
                </h2>
                <p className="mt-1 text-sm text-amber-800">
                  {driftRows.some((row) => row.locally_modified_files.length > 0)
                    ? 'Files were edited locally. Reinstall to overwrite, or keep your edits and re-verify.'
                    : 'A framework is out of date with the compiled setup. Reinstall when you are ready.'}
                </p>
              </div>
              <Link
                to={`/setups/${driftRows[0].profile_id}`}
                className="inline-flex items-center justify-center gap-2 rounded-lg border border-amber-300 bg-card px-4 py-2 text-sm font-medium text-amber-900 transition-colors hover:bg-amber-100"
              >
                Review changes
              </Link>
            </div>
          )}

          {setups.length > 0 && syncRows.length > 0 && driftRows.length === 0 && (
            <p className="flex items-center gap-2 text-sm text-muted-foreground">
              <CheckCircle2 className="h-4 w-4 text-green-600" />
              Every installed framework is in sync. Nothing needs your attention.
            </p>
          )}
        </>
      )}

      {/* Your setups */}
      {setups.length > 0 && (
        <section className="space-y-3">
          <div className="flex items-center justify-between">
            <h2 className="text-lg font-semibold text-foreground">Your setups</h2>
            <Link to="/setups" className="text-sm text-brand-600 hover:underline">
              View all
            </Link>
          </div>
          <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
            {setups.map((profile) => {
              const targets = profileTargets(profile);
              const packNames = packNamesFor(profile);
              return (
                <Link
                  key={profile.id}
                  to={`/setups/${profile.id}`}
                  className="rounded-xl border border-border bg-card p-5 transition-shadow hover:border-input hover:shadow-sm"
                >
                  <h3 className="font-semibold text-card-foreground">{profile.name}</h3>
                  <p className="mt-1 text-sm text-muted-foreground">
                    {packNames.length > 0 ? packNames.join(' · ') : 'No packs selected yet'}
                  </p>
                  <div className="mt-4 flex flex-wrap gap-1.5">
                    {targets.length === 0 && (
                      <span className="text-xs text-muted-foreground">No frameworks chosen</span>
                    )}
                    {targets.map((target) => {
                      const row = syncRows.find(
                        (status) => status.profile_id === profile.id && status.target === target,
                      );
                      const state = installState(row);
                      return (
                        <span
                          key={target}
                          className={`rounded-full border px-2.5 py-1 text-xs font-medium ${INSTALL_STATE_CLASSES[state]}`}
                        >
                          {target} — {INSTALL_STATE_LABELS[state]}
                        </span>
                      );
                    })}
                  </div>
                </Link>
              );
            })}

            <Link
              to="/setups"
              className="flex min-h-[9rem] flex-col items-center justify-center gap-2 rounded-xl border border-dashed border-border p-5 text-muted-foreground transition-colors hover:border-brand-300 hover:text-brand-700"
            >
              <Plus className="h-5 w-5" />
              <span className="text-sm font-medium">New setup</span>
            </Link>
          </div>
        </section>
      )}

      {/* Recommended packs */}
      <section className="space-y-3">
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-semibold text-foreground">Recommended packs</h2>
          <Link to="/packs" className="text-sm text-brand-600 hover:underline">
            Browse all
          </Link>
        </div>
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-4">
          {BUNDLES.map((bundle) => {
            const pack =
              basePacks.find(
                (collection) => collection.is_starter_pack && collection.name === bundle.basePackName,
              ) ?? basePacks.find((collection) => collection.name === bundle.basePackName);
            const source = pack ? packSource(pack) : null;
            const body = (
              <>
                <div className="flex items-center justify-between gap-2">
                  <span className="rounded bg-blue-50 px-2 py-0.5 text-xs font-medium text-blue-700">
                    Starting point
                  </span>
                  {source && (
                    <span className="rounded bg-brand-50 px-2 py-0.5 text-xs font-medium text-brand-700">
                      {packSourceLabel(source)}
                    </span>
                  )}
                </div>
                <h3 className="mt-3 font-semibold text-card-foreground">{bundle.name}</h3>
                <p className="mt-1 line-clamp-2 text-sm text-muted-foreground">{bundle.description}</p>
                <div className="mt-3 flex flex-wrap items-center gap-3 text-xs text-muted-foreground">
                  {pack && pack.rating_count > 0 && (
                    <span className="flex items-center gap-1">
                      <Star className="h-3 w-3" />
                      {pack.avg_rating.toFixed(1)}
                    </span>
                  )}
                  {pack && <span>{pack.artifact_count} items</span>}
                  {pack && <span>{pack.download_count} uses</span>}
                </div>
              </>
            );

            return pack ? (
              <Link
                key={bundle.id}
                to={`/packs/${pack.id}`}
                className="rounded-xl border border-border bg-card p-5 transition-shadow hover:border-input hover:shadow-sm"
              >
                {body}
              </Link>
            ) : (
              <div key={bundle.id} className="rounded-xl border border-border bg-card p-5">
                {body}
              </div>
            );
          })}
        </div>
      </section>

      {/* Community highlights */}
      <section className="space-y-3">
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-semibold text-foreground">Community highlights</h2>
          <Link to="/packs" className="text-sm text-brand-600 hover:underline">
            Browse community
          </Link>
        </div>
        {communityHighlights.length > 0 ? (
          <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-4">
            {communityHighlights.map((collection) => (
              <Link
                key={collection.id}
                to={`/packs/community/${collection.id}`}
                className="rounded-xl border border-border bg-card p-5 transition-shadow hover:border-input hover:shadow-sm"
              >
                <div className="flex items-center justify-between gap-2">
                  <span className="rounded bg-muted px-2 py-0.5 text-xs font-medium text-muted-foreground">
                    {collection.collection_type === 'base' ? 'Starting point' : 'Add-on'}
                  </span>
                  <span className="rounded border border-border px-2 py-0.5 text-xs text-muted-foreground">
                    Community
                  </span>
                </div>
                <h3 className="mt-3 font-semibold text-card-foreground">{collection.name}</h3>
                <p className="mt-1 line-clamp-2 text-sm text-muted-foreground">
                  {collection.description || 'No description'}
                </p>
                <div className="mt-3 flex flex-wrap items-center gap-3 text-xs text-muted-foreground">
                  {collection.rating_count > 0 && (
                    <span className="flex items-center gap-1">
                      <Star className="h-3 w-3" />
                      {collection.avg_rating.toFixed(1)}
                    </span>
                  )}
                  <span>{collection.download_count} uses</span>
                  {collection.last_verified_at && <span>verified</span>}
                </div>
              </Link>
            ))}
          </div>
        ) : (
          <p className="flex items-center gap-2 text-sm text-muted-foreground">
            <FolderGit2 className="h-4 w-4" />
            No community packs yet. Publish one of yours to start the shelf.
          </p>
        )}
      </section>

      <p className="text-sm text-muted-foreground">
        {frameworkCount} frameworks supported · MyACE v{appVersion} ·{' '}
        <a
          href="https://github.com/niels-emmer/myace"
          target="_blank"
          rel="noopener noreferrer"
          className="text-brand-600 hover:underline"
        >
          source
        </a>
      </p>
    </div>
  );
}
