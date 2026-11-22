import { useMemo, useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import { useMutation, useQuery, useQueries, useQueryClient } from '@tanstack/react-query';
import {
  AlertTriangle,
  ArrowLeft,
  Check,
  Copy,
  Download,
  FolderGit2,
  Globe,
  Layers,
  Lock,
  Pencil,
  Plus,
  Trash2,
  X,
} from 'lucide-react';
import { adaptersApi, collectionsApi, profilesApi, syncApi } from '../lib/api';
import { installsApi, profileToCreate, setupProfilesApi } from '../lib/setupApi';
import { frameworkLabel } from '../lib/packs';
import { useAuth } from '../contexts/AuthContext';
import ProfileFormFields from '../components/ProfileForm';
import { buildFrameworkRows, profileTargets, resolveInstallPath } from '../types/setup';
import type { InstallState, SetupProfileCreate } from '../types/setup';
import type { ArtifactType, ProfileCompileRequest, ProfileCreate } from '../types';

const TYPE_ORDER: ArtifactType[] = ['rule', 'workflow', 'agent', 'skill', 'model_config'];
const TYPE_LABELS: Record<ArtifactType, string> = {
  rule: 'Rules',
  workflow: 'Workflows',
  agent: 'Agents',
  skill: 'Skills',
  model_config: 'Model Configs',
};

const STATE_LABELS: Record<InstallState, string> = {
  verified: 'Verified in sync',
  drift: 'Changes since install',
  unverified: 'Installed, not verified',
  'not-installed': 'Not installed',
};

const STATE_CLASSES: Record<InstallState, string> = {
  verified: 'bg-green-50 text-green-700 border-green-200',
  drift: 'bg-amber-50 text-amber-700 border-amber-200',
  unverified: 'bg-blue-50 text-blue-700 border-blue-200',
  'not-installed': 'bg-muted text-muted-foreground border-border',
};

/**
 * The label the server put in a `pack_unavailable` message. Owner-visible
 * messages carry `'Name' (shortid)`; a non-owner only ever sees `'shortid'`.
 */
function packUnavailableLabel(message: string): string {
  const match = message.match(/^Pack (.+?) (?:is|was)\b/);
  return match?.[1] ?? 'A pack';
}

function canSeeFrozenContent(
  viewerId: string | undefined,
  isAdmin: boolean | undefined,
  ownerId: string,
): boolean {
  return viewerId === ownerId || Boolean(isAdmin);
}

export default function ProfileDetail() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { user } = useAuth();
  const [isEditing, setIsEditing] = useState(false);
  const [editForm, setEditForm] = useState<ProfileCreate | null>(null);
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
  const [addPackId, setAddPackId] = useState('');
  const [dismissedWarnings, setDismissedWarnings] = useState<string[]>([]);
  const [copiedCommand, setCopiedCommand] = useState<string | null>(null);

  const { data: profile, isLoading: loadingProfile } = useQuery({
    queryKey: ['profile', id],
    queryFn: () => profilesApi.get(id!),
    enabled: !!id,
  });

  const { data: collections } = useQuery({
    queryKey: ['collections'],
    queryFn: () => collectionsApi.list(),
  });

  const { data: adapters } = useQuery({
    queryKey: ['adapters'],
    queryFn: () => adaptersApi.list(),
  });

  const { data: syncRows } = useQuery({
    queryKey: ['sync-status'],
    queryFn: () => syncApi.getStatus(),
  });

  const { data: claims } = useQuery({
    queryKey: ['installs', id],
    queryFn: () => installsApi.list(id!),
    enabled: !!id,
  });

  const profileFrameworks = profile ? profileTargets(profile) : [];
  // Compile-time warnings only come from a compile. The first configured
  // framework is enough: pack availability and cross-pack collisions do not
  // vary by target.
  const warningTarget = profileFrameworks[0] ?? 'opencode';
  const { data: warningsResult } = useQuery({
    queryKey: ['profile-warnings', id, warningTarget],
    queryFn: () =>
      profilesApi.compile({
        profile_id: id!,
        target: warningTarget,
      } satisfies ProfileCompileRequest),
    enabled: !!profile && profileFrameworks.length > 0,
  });
  const warnings = warningsResult?.warnings ?? [];

  const baseCollections = collections?.filter((c) => c.collection_type === 'base') ?? [];
  const additionalCollections =
    collections?.filter((c) => c.collection_type === 'additional') ?? [];
  const collectionById = new Map((collections ?? []).map((c) => [c.id, c]));
  const collectionName = (cid: string) => collectionById.get(cid)?.name ?? cid;

  // Combined items, deduplicated by name the way compile_profile() does
  // (later packs win), so the counts match what an install actually writes.
  const resourceCollectionIds = profile
    ? [profile.base_collection_id, ...profile.additional_collection_ids]
    : [];
  const artifactQueries = useQueries({
    queries: resourceCollectionIds.map((cid) => ({
      queryKey: ['artifacts', cid, { include_disabled: false }],
      queryFn: () => collectionsApi.getArtifacts(cid),
      enabled: !!profile,
    })),
  });
  const resourcesLoading = artifactQueries.some((q) => q.isLoading);
  const allArtifacts = artifactQueries.flatMap((query) => query.data ?? []);

  const disabledSet = useMemo(
    () => new Set(profile?.disabled_artifact_ids ?? []),
    [profile?.disabled_artifact_ids],
  );

  const resourceCounts: Partial<Record<ArtifactType, number>> = {};
  const seenArtifactTypes = new Map<string, ArtifactType>();
  for (const artifact of allArtifacts) {
    if (disabledSet.has(artifact.id)) continue;
    seenArtifactTypes.set(artifact.name, artifact.artifact_type);
  }
  for (const type of seenArtifactTypes.values()) {
    resourceCounts[type] = (resourceCounts[type] ?? 0) + 1;
  }
  const resourceTotal = Object.values(resourceCounts).reduce((total, n) => total + (n ?? 0), 0);

  const frameworkRows = useMemo(
    () => (profile ? buildFrameworkRows(profile, syncRows ?? [], claims ?? []) : []),
    [profile, syncRows, claims],
  );

  const payloadFor = (patch: Partial<SetupProfileCreate>): SetupProfileCreate =>
    profileToCreate(profile!, patch);

  const updateMutation = useMutation({
    mutationFn: (data: SetupProfileCreate) => setupProfilesApi.update(id!, data),
    onSuccess: (updated) => {
      queryClient.setQueryData(['profile', id], updated);
      queryClient.invalidateQueries({ queryKey: ['profiles'] });
      queryClient.invalidateQueries({ queryKey: ['profile-warnings', id] });
      queryClient.invalidateQueries({ queryKey: ['installs', id] });
      setIsEditing(false);
      setAddPackId('');
    },
  });

  const deleteMutation = useMutation({
    mutationFn: () => profilesApi.delete(id!),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['profiles'] });
      navigate('/setups');
    },
  });

  if (loadingProfile) {
    return <div className="py-12 text-center text-muted-foreground">Loading setup…</div>;
  }

  if (!profile) {
    return <div className="py-12 text-center text-muted-foreground">Setup not found.</div>;
  }

  const targets = (adapters ?? []).map((a) => a.name);
  const canSeeFrozen = canSeeFrozenContent(user?.id, user?.is_admin, profile.owner_id);

  const startEdit = () => {
    updateMutation.reset();
    setEditForm({
      name: profile.name,
      description: profile.description ?? '',
      base_collection_id: profile.base_collection_id,
      additional_collection_ids: [...profile.additional_collection_ids],
      disabled_artifact_ids: [...profile.disabled_artifact_ids],
      target_framework: profile.target_framework,
      is_public: profile.is_public,
    });
    setIsEditing(true);
  };

  const saveEdit = () => {
    if (!editForm) return;
    updateMutation.mutate(
      payloadFor({
        name: editForm.name,
        description: editForm.description,
        base_collection_id: editForm.base_collection_id,
        additional_collection_ids: editForm.additional_collection_ids ?? [],
        disabled_artifact_ids: editForm.disabled_artifact_ids ?? [],
        is_public: editForm.is_public,
        // The legacy single "preferred target" is a preference, not the
        // multi-framework list. Persist it without dropping frameworks.
        target_framework: editForm.target_framework,
        target_frameworks: profileFrameworks,
      }),
    );
  };

  const addPackCandidates = additionalCollections.filter(
    (collection) => !profile.additional_collection_ids.includes(collection.id),
  );

  const addPack = () => {
    if (!addPackId) return;
    updateMutation.mutate(
      payloadFor({
        additional_collection_ids: [...profile.additional_collection_ids, addPackId],
      }),
    );
  };

  const removePack = (collectionId: string) => {
    updateMutation.mutate(
      payloadFor({
        additional_collection_ids: profile.additional_collection_ids.filter(
          (cid) => cid !== collectionId,
        ),
      }),
    );
  };

  const toggleFramework = (target: string) => {
    const next = profileFrameworks.includes(target)
      ? profileFrameworks.filter((framework) => framework !== target)
      : [...profileFrameworks, target];
    // Keep the deprecated single target consistent with the list; otherwise a
    // removed legacy target would keep reappearing through the fallback.
    const legacy = next.includes(profile.target_framework ?? '')
      ? profile.target_framework
      : (next[0] ?? undefined);
    updateMutation.mutate(
      payloadFor({ target_frameworks: next, target_framework: legacy }),
    );
  };

  const toggleArtifact = (artifactId: string) => {
    const disabled = profile.disabled_artifact_ids.includes(artifactId)
      ? profile.disabled_artifact_ids.filter((aid) => aid !== artifactId)
      : [...profile.disabled_artifact_ids, artifactId];
    updateMutation.mutate(payloadFor({ disabled_artifact_ids: disabled }));
  };

  const copyVerify = async (target: string) => {
    const command = `myace check --target ${target} --report`;
    await navigator.clipboard.writeText(command);
    setCopiedCommand(target);
    setTimeout(() => setCopiedCommand(null), 2000);
  };

  /**
   * Packs named by a `pack_unavailable` warning -> whether the server said a
   * frozen copy was used. The *message* decides, not the viewer: an owner can
   * receive the "skipped" variant when no snapshot was captured.
   */
  const unavailableWarningPacks = new Map<string, boolean>();
  for (const warning of warnings) {
    if (warning.code !== 'pack_unavailable') continue;
    const known = [...baseCollections, ...additionalCollections].find(
      (collection) => warning.message.includes(collection.name),
    );
    if (known) {
      unavailableWarningPacks.set(known.id, /using a frozen copy/i.test(warning.message));
    }
  }

  const visibleWarnings = warnings.filter(
    (warning) => !dismissedWarnings.includes(`${warning.code}:${warning.message}`),
  );

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-start gap-4">
        <button
          type="button"
          onClick={() => navigate('/setups')}
          className="-ml-2 rounded-lg p-2 text-muted-foreground transition-colors hover:bg-accent hover:text-accent-foreground"
          title="Back to setups"
        >
          <ArrowLeft className="h-5 w-5" />
        </button>

        <div className="min-w-0 flex-1">
          {isEditing && editForm ? (
            <div className="max-w-2xl">
              <ProfileFormFields
                value={editForm}
                onChange={setEditForm}
                baseCollections={baseCollections}
                additionalCollections={additionalCollections}
                targets={targets}
              />
            </div>
          ) : (
            <>
              <div className="flex items-center gap-3">
                <h1 className="truncate text-2xl font-bold text-foreground">{profile.name}</h1>
                <span
                  className={`shrink-0 rounded px-2 py-0.5 text-xs font-medium ${
                    profile.is_public
                      ? 'bg-green-50 text-green-700'
                      : 'bg-muted text-muted-foreground'
                  }`}
                >
                  {profile.is_public ? 'Public' : 'Private'}
                </span>
                <span className="shrink-0 text-xs text-muted-foreground">
                  v{profile.version}
                </span>
              </div>
              <p className="mt-1 text-muted-foreground">
                {profile.description || 'No description'}
              </p>
              <div className="mt-2 flex items-center gap-4 text-xs text-muted-foreground">
                <span className="flex items-center gap-1">
                  {profile.is_public ? <Globe className="h-3 w-3" /> : <Lock className="h-3 w-3" />}
                  {profile.is_public ? 'public' : 'private'}
                </span>
                {profileFrameworks.length > 0 && (
                  <span>
                    {profileFrameworks.length} framework
                    {profileFrameworks.length === 1 ? '' : 's'}
                  </span>
                )}
              </div>
            </>
          )}
        </div>

        <div className="flex shrink-0 items-center gap-2">
          {isEditing ? (
            <>
              <button
                type="button"
                onClick={() => setIsEditing(false)}
                className="flex items-center gap-1.5 px-3 py-2 text-sm text-muted-foreground transition-colors hover:text-accent-foreground"
              >
                <X className="h-4 w-4" />
                Cancel
              </button>
              <button
                type="button"
                onClick={saveEdit}
                disabled={
                  !editForm?.name.trim() ||
                  !editForm?.base_collection_id ||
                  updateMutation.isPending
                }
                className="flex items-center gap-1.5 rounded-lg bg-brand-600 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-brand-700 disabled:opacity-50"
              >
                <Check className="h-4 w-4" />
                {updateMutation.isPending ? 'Saving…' : 'Save'}
              </button>
            </>
          ) : (
            <>
              <Link
                to={`/setups/${profile.id}/install`}
                className="flex items-center gap-1.5 rounded-lg bg-brand-600 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-brand-700"
              >
                <Download className="h-3.5 w-3.5" />
                Install
              </Link>
              <button
                type="button"
                onClick={() => navigate('/setups', { state: { cloneFrom: profile } })}
                className="flex items-center gap-1.5 rounded-lg border border-border bg-muted px-4 py-2 text-sm text-foreground transition-colors hover:bg-accent"
              >
                <Copy className="h-3.5 w-3.5" />
                Clone
              </button>
              <button
                type="button"
                onClick={() => setShowDeleteConfirm(true)}
                className="flex items-center gap-1.5 rounded-lg border border-border bg-muted px-4 py-2 text-sm text-destructive transition-colors hover:bg-destructive/10"
              >
                <Trash2 className="h-3.5 w-3.5" />
                Delete
              </button>
              <button
                type="button"
                onClick={startEdit}
                className="flex items-center gap-1.5 rounded-lg border border-border bg-muted px-4 py-2 text-sm text-foreground transition-colors hover:bg-accent"
              >
                <Pencil className="h-3.5 w-3.5" />
                Edit
              </button>
            </>
          )}
        </div>
      </div>

      {updateMutation.isError && (
        <div className="rounded-lg border border-destructive/30 bg-destructive/10 p-3 text-sm text-destructive">
          {(updateMutation.error as Error).message}
        </div>
      )}

      {/* Packs */}
      {!isEditing && (
        <div className="space-y-4 rounded-xl border border-border bg-card p-6">
          <div className="flex items-center justify-between">
            <h2 className="text-sm font-medium text-muted-foreground">Packs in this setup</h2>
            {addPackCandidates.length > 0 && (
              <div className="flex items-center gap-2">
                <label htmlFor="add-pack" className="sr-only">
                  Pack to add
                </label>
                <select
                  id="add-pack"
                  value={addPackId}
                  onChange={(event) => setAddPackId(event.target.value)}
                  className="rounded-lg border border-input bg-background px-2 py-1.5 text-sm text-foreground"
                >
                  <option value="">Choose a pack…</option>
                  {addPackCandidates.map((collection) => (
                    <option key={collection.id} value={collection.id}>
                      {collection.name}
                    </option>
                  ))}
                </select>
                <button
                  type="button"
                  onClick={addPack}
                  disabled={!addPackId || updateMutation.isPending}
                  className="flex items-center gap-1 rounded-lg border border-border px-3 py-1.5 text-sm text-foreground transition-colors hover:bg-accent disabled:opacity-50"
                >
                  <Plus className="h-3.5 w-3.5" />
                  Add pack
                </button>
              </div>
            )}
          </div>

          <div className="overflow-hidden rounded-lg border border-border">
            <div className="flex items-center gap-2 border-b border-border px-4 py-3">
              <span className="rounded bg-blue-50 px-2 py-0.5 text-xs font-medium text-blue-700">
                Starting point
              </span>
              <Link
                to={`/packs/${profile.base_collection_id}`}
                className="text-sm font-medium text-foreground hover:underline"
              >
                {collectionName(profile.base_collection_id)}
              </Link>
              {unavailableWarningPacks.has(profile.base_collection_id) && (
                <span className="ml-auto rounded border border-amber-200 bg-amber-50 px-2 py-0.5 text-xs text-amber-700">
                  {canSeeFrozen && unavailableWarningPacks.get(profile.base_collection_id)
                    ? 'frozen'
                    : 'unavailable'}
                </span>
              )}
            </div>
            {profile.additional_collection_ids.map((cid) => (
              <div key={cid} className="flex items-center gap-2 border-b border-border px-4 py-3 last:border-b-0">
                <span className="rounded bg-purple-50 px-2 py-0.5 text-xs font-medium text-purple-700">
                  Add-on
                </span>
                <Link
                  to={`/packs/${cid}`}
                  className="text-sm font-medium text-foreground hover:underline"
                >
                  {collectionName(cid)}
                </Link>
                {unavailableWarningPacks.has(cid) && (
                  <span className="rounded border border-amber-200 bg-amber-50 px-2 py-0.5 text-xs text-amber-700">
                    {canSeeFrozen && unavailableWarningPacks.get(cid)
                      ? 'frozen'
                      : 'unavailable'}
                  </span>
                )}
                <button
                  type="button"
                  onClick={() => removePack(cid)}
                  disabled={updateMutation.isPending}
                  aria-label={`Remove ${collectionName(cid)}`}
                  className="ml-auto rounded p-1 text-muted-foreground transition-colors hover:bg-accent hover:text-destructive disabled:opacity-50"
                >
                  <X className="h-4 w-4" />
                </button>
              </div>
            ))}
            {profile.additional_collection_ids.length === 0 && (
              <div className="px-4 py-3 text-sm text-muted-foreground">No add-ons yet.</div>
            )}
          </div>

          <p className="text-xs text-muted-foreground">
            {resourcesLoading
              ? 'Counting items…'
              : `${resourceTotal} item${resourceTotal === 1 ? '' : 's'} · ${TYPE_ORDER.filter(
                  (type) => resourceCounts[type],
                )
                  .map((type) => `${resourceCounts[type]} ${TYPE_LABELS[type].toLowerCase()}`)
                  .join(', ')}`}
          </p>
        </div>
      )}

      {/* Warnings */}
      {visibleWarnings.length > 0 && (
        <div className="space-y-3 rounded-xl border border-border bg-card p-6">
          <h2 className="text-sm font-medium text-muted-foreground">Compilation warnings</h2>
          {visibleWarnings.map((warning) => {
            const key = `${warning.code}:${warning.message}`;
            if (warning.code === 'pack_unavailable') {
              const label = packUnavailableLabel(warning.message);
              // Both the server variant and the viewer matter: never claim a
              // frozen copy that the compile did not actually fall back to,
              // and never reveal one to a non-owner.
              const usesFrozenCopy =
                canSeeFrozen && /using a frozen copy/i.test(warning.message);
              return (
                <div
                  key={key}
                  className="flex items-start gap-3 rounded-lg border border-amber-200 bg-amber-50 p-4"
                >
                  <AlertTriangle className="mt-0.5 h-5 w-5 shrink-0 text-amber-600" />
                  <div className="min-w-0 flex-1">
                    <p className="text-sm font-semibold text-amber-900">
                      Pack {label} is no longer available
                    </p>
                    {usesFrozenCopy ? (
                      <>
                        <p className="mt-1 text-sm text-amber-800">
                          Your setup keeps using a frozen copy, so nothing breaks. Find a
                          replacement or customize a copy to keep editing it.
                        </p>
                        <div className="mt-2 flex flex-wrap gap-2">
                          <button
                            type="button"
                            onClick={() =>
                              setDismissedWarnings((current) => [...current, key])
                            }
                            className="rounded border border-amber-300 px-2.5 py-1 text-xs font-medium text-amber-900 transition-colors hover:bg-amber-100"
                          >
                            Keep frozen
                          </button>
                          <Link
                            to="/packs/import"
                            className="rounded border border-amber-300 px-2.5 py-1 text-xs font-medium text-amber-900 transition-colors hover:bg-amber-100"
                          >
                            Customize a copy
                          </Link>
                        </div>
                      </>
                    ) : (
                      <p className="mt-1 text-sm text-amber-800">
                        It is skipped in this setup’s compiled output.
                      </p>
                    )}
                  </div>
                  <button
                    type="button"
                    onClick={() => setDismissedWarnings((current) => [...current, key])}
                    aria-label="Dismiss warning"
                    className="shrink-0 rounded p-1 transition-colors hover:bg-amber-100"
                  >
                    <X className="h-4 w-4 text-amber-600" />
                  </button>
                </div>
              );
            }
            return (
              <div
                key={key}
                className="flex items-start gap-3 rounded-lg border border-amber-200 bg-amber-50 p-4"
              >
                <AlertTriangle className="mt-0.5 h-5 w-5 shrink-0 text-amber-600" />
                <p className="min-w-0 flex-1 text-sm text-amber-800">{warning.message}</p>
                <button
                  type="button"
                  onClick={() => setDismissedWarnings((current) => [...current, key])}
                  aria-label="Dismiss warning"
                  className="shrink-0 rounded p-1 transition-colors hover:bg-amber-100"
                >
                  <X className="h-4 w-4 text-amber-600" />
                </button>
              </div>
            );
          })}
          <p className="text-xs text-muted-foreground">Warnings never block install.</p>
        </div>
      )}

      {/* Framework matrix */}
      {!isEditing && (
        <div className="overflow-hidden rounded-xl border border-border bg-card">
          <div className="flex items-center justify-between px-5 py-4">
            <h2 className="text-sm font-medium text-muted-foreground">Frameworks</h2>
            <Link to="/machine" className="text-sm text-brand-600 hover:underline">
              Check my machine
            </Link>
          </div>
          {frameworkRows.length === 0 ? (
            <p className="px-5 pb-5 text-sm text-muted-foreground">
              No frameworks configured. Edit the setup to choose one.
            </p>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead className="border-y border-border bg-muted/50 text-left text-xs text-muted-foreground">
                  <tr>
                    <th className="px-5 py-2 font-medium">Framework</th>
                    <th className="px-5 py-2 font-medium">Status</th>
                    <th className="px-5 py-2 font-medium">Location</th>
                    <th className="px-5 py-2 font-medium">Last verified</th>
                    <th className="px-5 py-2 text-right font-medium">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {frameworkRows.map((row) => (
                    <tr key={row.target} className="border-b border-border last:border-b-0">
                      <td className="px-5 py-3 font-medium text-foreground">{frameworkLabel(row.target)}</td>
                      <td className="px-5 py-3">
                        <span
                          className={`inline-flex rounded-full border px-2.5 py-1 text-xs font-medium ${STATE_CLASSES[row.state]}`}
                        >
                          {STATE_LABELS[row.state]}
                        </span>
                      </td>
                      <td className="px-5 py-3 font-mono text-xs text-muted-foreground">
                        {row.location
                          ? resolveInstallPath(row.target, row.location)
                          : '—'}
                      </td>
                      <td className="px-5 py-3 text-xs text-muted-foreground">
                        {row.lastVerifiedAt
                          ? new Date(row.lastVerifiedAt).toLocaleDateString()
                          : '—'}
                      </td>
                      <td className="px-5 py-3 text-right">
                        <div className="flex flex-wrap items-center justify-end gap-2">
                          {row.state === 'unverified' && (
                            <button
                              type="button"
                              onClick={() => copyVerify(row.target)}
                              className="rounded border border-border px-2.5 py-1 text-xs font-medium text-foreground transition-colors hover:bg-accent"
                            >
                              {copiedCommand === row.target ? 'Copied' : 'Verify'}
                            </button>
                          )}
                          <Link
                            to={`/setups/${profile.id}/install?target=${row.target}`}
                            className="rounded border border-border px-2.5 py-1 text-xs font-medium text-foreground transition-colors hover:bg-accent"
                          >
                            {row.state === 'not-installed' ? 'Install' : 'Reinstall'}
                          </Link>
                          <Link
                            to={`/setups/${profile.id}/install?target=${row.target}`}
                            className="rounded px-2.5 py-1 text-xs font-medium text-muted-foreground transition-colors hover:bg-accent"
                          >
                            View files
                          </Link>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {/* Advanced */}
      {!isEditing && (
        <details className="rounded-xl border border-border bg-card">
          <summary className="cursor-pointer px-5 py-4 text-sm font-medium text-muted-foreground">
            Advanced — item toggles, compiled preview, raw membership
          </summary>
          <div className="space-y-4 px-5 pb-5">
            <p className="text-xs text-muted-foreground">
              Toggle individual items. Disabled items stay in their pack but are left out of
              this setup.
            </p>
            {resourcesLoading ? (
              <p className="text-sm text-muted-foreground">Loading items…</p>
            ) : (
              <ul className="max-h-72 divide-y divide-border overflow-y-auto rounded-lg border border-border">
                {[...allArtifacts]
                  .sort((a, b) => a.name.localeCompare(b.name))
                  .map((artifact) => (
                    <li key={artifact.id} className="flex items-center gap-3 px-3 py-2">
                      <input
                        id={`artifact-${artifact.id}`}
                        type="checkbox"
                        checked={!disabledSet.has(artifact.id)}
                        onChange={() => toggleArtifact(artifact.id)}
                        className="h-4 w-4"
                      />
                      <label
                        htmlFor={`artifact-${artifact.id}`}
                        className="min-w-0 flex-1 truncate text-sm text-foreground"
                      >
                        {artifact.name}
                      </label>
                      <span className="text-xs text-muted-foreground">
                        {artifact.artifact_type}
                      </span>
                    </li>
                  ))}
                {allArtifacts.length === 0 && (
                  <li className="px-3 py-3 text-sm text-muted-foreground">No items yet.</li>
                )}
              </ul>
            )}
            <div>
              <p className="mb-2 text-xs text-muted-foreground">Frameworks in this setup</p>
              <div className="flex flex-wrap gap-2">
                {(adapters ?? [])
                  .filter(
                    (adapter) =>
                      // Keep a selected framework visible even if an admin has
                      // since disabled its adapter, so it can be removed.
                      adapter.enabled || profileFrameworks.includes(adapter.name),
                  )
                  .map((adapter) => {
                    const selected = profileFrameworks.includes(adapter.name);
                    return (
                      <button
                        key={adapter.name}
                        type="button"
                        aria-pressed={selected}
                        onClick={() => toggleFramework(adapter.name)}
                        disabled={updateMutation.isPending}
                        className={`rounded-lg border px-3 py-1.5 text-xs font-medium transition-colors disabled:opacity-50 ${
                          selected
                            ? 'border-brand-500 bg-brand-50 text-brand-700'
                            : 'border-border text-muted-foreground hover:border-input'
                        }`}
                      >
                        {frameworkLabel(adapter.name)}
                      </button>
                    );
                  })}
                {(adapters ?? []).filter(
                  (adapter) => adapter.enabled || profileFrameworks.includes(adapter.name),
                ).length === 0 && (
                  <span className="text-xs text-muted-foreground">
                    No adapters are enabled.
                  </span>
                )}
              </div>
            </div>
            <div className="flex flex-wrap items-center gap-3">
              <Link
                to={`/setups/${profile.id}/install`}
                className="rounded-lg border border-border px-3 py-1.5 text-sm text-foreground transition-colors hover:bg-accent"
              >
                Open compiled preview
              </Link>
              <span className="flex items-center gap-1.5 text-xs text-muted-foreground">
                <Layers className="h-3.5 w-3.5" />
                {resourceCollectionIds.join(' · ')}
              </span>
            </div>
            <p className="flex items-center gap-1.5 text-xs text-muted-foreground">
              <FolderGit2 className="h-3.5 w-3.5" />
              Raw membership: base {profile.base_collection_id}
              {profile.additional_collection_ids.length > 0
                ? `, add-ons ${profile.additional_collection_ids.join(', ')}`
                : ''}
            </p>
          </div>
        </details>
      )}

      {/* Delete confirmation — the codebase's existing modal pattern (rule 28). */}
      {showDeleteConfirm && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
          <div className="w-full max-w-sm space-y-4 rounded-xl border border-border bg-card p-6">
            <div className="flex items-start gap-3">
              <div className="shrink-0 rounded-lg bg-destructive/10 p-2">
                <AlertTriangle className="h-5 w-5 text-destructive" />
              </div>
              <div>
                <h2 className="text-lg font-semibold text-card-foreground">
                  Delete “{profile.name}”?
                </h2>
                <p className="mt-1 text-sm text-muted-foreground">
                  This action cannot be undone.
                </p>
              </div>
            </div>

            {deleteMutation.isError && (
              <p className="text-sm text-destructive">
                {(deleteMutation.error as Error).message}
              </p>
            )}

            <div className="flex justify-end gap-3">
              <button
                type="button"
                onClick={() => setShowDeleteConfirm(false)}
                className="px-4 py-2 text-sm text-muted-foreground hover:text-accent-foreground"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={() => deleteMutation.mutate()}
                disabled={deleteMutation.isPending}
                className="rounded-lg bg-destructive px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-destructive/90 disabled:opacity-50"
              >
                {deleteMutation.isPending ? 'Deleting…' : 'Delete'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
