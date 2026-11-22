import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { Check, FolderGit2, Loader2, Plus } from 'lucide-react';
import { collectionsApi, profilesApi } from '../lib/api';
import { packUsageApi, profileToCreate, setupProfilesApi } from '../lib/setupApi';
import { useAuth } from '../contexts/AuthContext';
import { packKindLabel } from '../lib/packs';
import type { CollectionType, Profile } from '../types';

/**
 * "Use this pack" / "Add to a setup" for a pack detail page.
 *
 * Design 6.5 requires both to actually attach the pack to a setup — not just
 * bump `download_count` (that counter is advisory, invariant 25 / ADR-0015).
 * A starting point creates a setup with that base; an add-on first asks which
 * starting point to pair with (most-used preselected) and then creates a setup
 * with both. "Add to a setup" updates one of the user's existing setups.
 *
 * Kept as its own component so the pack-detail pages just mount it.
 */
const PROFILE_NAME_MAX = 255;

/** `Profile.name` is String(255); generated names must never exceed it. */
function generatedSetupName(packName: string): string {
  const suffix = ' setup';
  if (packName.length + suffix.length <= PROFILE_NAME_MAX) return `${packName}${suffix}`;
  return `${packName.slice(0, PROFILE_NAME_MAX - suffix.length)}${suffix}`;
}

/** The subset of a pack this flow needs — `Pack` and `Collection` both fit. */
export interface AddToSetupPack {
  id: string;
  name: string;
  description?: string;
  collection_type: CollectionType;
  artifact_count: number;
  download_count: number;
}

export default function AddToSetup({
  collection,
  showUse = true,
  frameworks = [],
}: {
  collection: AddToSetupPack;
  /** Callers that supply their own "Use this pack" flow mount the menu only. */
  showUse?: boolean;
  /** Adapter names the pack declares (artifact target_compatibility); filtered server-side. */
  frameworks?: string[];
}) {
  const { user } = useAuth();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [menuOpen, setMenuOpen] = useState(false);
  const [pairingOpen, setPairingOpen] = useState(false);
  const [selectedBaseId, setSelectedBaseId] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const isBase = collection.collection_type === 'base';

  const { data: profiles } = useQuery({
    queryKey: ['profiles', { owner_id: user?.id }],
    queryFn: () => profilesApi.list({ owner_id: user?.id }),
    enabled: !!user,
  });
  const { data: collections } = useQuery({
    queryKey: ['collections'],
    queryFn: () => collectionsApi.list(),
  });

  const ownSetups = (profiles ?? []).filter((profile) => profile.owner_id === user?.id);
  const basePacks = (collections ?? []).filter((pack) => pack.collection_type === 'base');
  const mostUsedBase = [...basePacks].sort(
    (a, b) => (b.download_count ?? 0) - (a.download_count ?? 0),
  )[0];

  // Advisory counter only — a failure here must never fail the attach.
  const recordUse = () => {
    void packUsageApi.use(collection.id).catch(() => {});
  };

  const finish = (profile: Profile) => {
    queryClient.invalidateQueries({ queryKey: ['profiles'] });
    queryClient.invalidateQueries({ queryKey: ['profile', profile.id] });
    navigate(`/setups/${profile.id}`);
  };

  const createSetup = async (baseId: string, addOnIds: string[]) => {
    setBusy(true);
    setError(null);
    try {
      const created = await setupProfilesApi.create({
        name: generatedSetupName(collection.name),
        description: collection.description,
        base_collection_id: baseId,
        additional_collection_ids: addOnIds,
        disabled_artifact_ids: [],
        // Prefer whatever the pack declares; if it declares nothing the user
        // lands on the setup page, where Advanced adds frameworks — never on
        // an install screen with nothing to install.
        target_frameworks: frameworks,
      });
      recordUse();
      finish(created);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  };

  const attachTo = async (profile: Profile) => {
    setError(null);
    // Guard before setting busy: an early return must not leave the panel stuck
    // with every control disabled.
    if (isBase && profile.base_collection_id === collection.id) {
      // Already this setup's base — nothing to write, and no counter bump.
      setMenuOpen(false);
      finish(profile);
      return;
    }
    // A pack cannot be both the base and an add-on of the same setup.
    if (!isBase && profile.base_collection_id === collection.id) {
      setError('This pack is already this setup’s starting point.');
      setMenuOpen(false);
      return;
    }
    if (!isBase && profile.additional_collection_ids.includes(collection.id)) {
      // Already attached — nothing to write, and no reason to bump the counter.
      setMenuOpen(false);
      finish(profile);
      return;
    }
    setBusy(true);
    try {
      const additional = isBase
        ? // A pack becoming the base must not also remain an add-on.
          profile.additional_collection_ids.filter((id) => id !== collection.id)
        : [...profile.additional_collection_ids, collection.id];
      const updated = await setupProfilesApi.update(
        profile.id,
        profileToCreate(profile, {
          base_collection_id: isBase ? collection.id : profile.base_collection_id,
          additional_collection_ids: additional,
        }),
      );
      recordUse();
      setMenuOpen(false);
      finish(updated);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  };

  const startUse = () => {
    setError(null);
    if (isBase) {
      void createSetup(collection.id, []);
      return;
    }
    setPairingOpen(true);
    setSelectedBaseId(mostUsedBase?.id ?? basePacks[0]?.id ?? '');
  };

  return (
    <div className="space-y-2">
      {showUse && (
        <button
          type="button"
          onClick={startUse}
          disabled={busy || (!isBase && basePacks.length === 0)}
          className="flex w-full items-center justify-center gap-2 rounded-lg bg-brand-600 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-brand-700 disabled:opacity-50"
        >
          {busy ? <Loader2 className="h-4 w-4 animate-spin" /> : <Check className="h-4 w-4" />}
          Use this pack
        </button>
      )}

      <div>
        <button
          type="button"
          onClick={() => setMenuOpen((open) => !open)}
          aria-expanded={menuOpen}
          className="flex w-full items-center justify-center gap-2 rounded-lg border border-border px-4 py-2 text-sm text-foreground transition-colors hover:bg-accent"
        >
          <Plus className="h-4 w-4" />
          Add to a setup…
        </button>
        {menuOpen && (
          <div className="mt-2 overflow-hidden rounded-lg border border-border">
            {ownSetups.length === 0 ? (
              <p className="px-3 py-2 text-xs text-muted-foreground">
                No setups yet — use this pack to create one.
              </p>
            ) : (
              ownSetups.map((profile) => (
                <button
                  key={profile.id}
                  type="button"
                  disabled={busy}
                  onClick={() => attachTo(profile)}
                  className="flex w-full items-center gap-2 border-b border-border px-3 py-2 text-left text-sm text-foreground transition-colors last:border-b-0 hover:bg-accent disabled:opacity-50"
                >
                  <FolderGit2 className="h-4 w-4 flex-shrink-0 text-muted-foreground" />
                  <span className="min-w-0 flex-1 truncate">{profile.name}</span>
                  <span className="text-xs text-muted-foreground">
                    {profile.additional_collection_ids.length + 1} packs
                  </span>
                </button>
              ))
            )}
          </div>
        )}
      </div>

      {pairingOpen && !isBase && (
        <div className="space-y-2 rounded-lg border border-brand-200 bg-brand-50 p-3">
          <p className="text-xs font-medium text-brand-900">
            {packKindLabel(collection.collection_type)} — choose a starting point to pair it
            with
          </p>
          <div className="space-y-1">
            {basePacks.map((pack) => (
              <label
                key={pack.id}
                className="flex items-center gap-2 rounded border border-brand-200 bg-card px-2 py-1.5 text-xs"
              >
                <input
                  type="radio"
                  name="add-to-setup-base"
                  value={pack.id}
                  checked={selectedBaseId === pack.id}
                  onChange={() => setSelectedBaseId(pack.id)}
                />
                <span className="font-medium text-foreground">{pack.name}</span>
                <span className="ml-auto text-muted-foreground">{pack.artifact_count} items</span>
              </label>
            ))}
          </div>
          <div className="flex gap-2">
            <button
              type="button"
              disabled={!selectedBaseId || busy}
              onClick={() => void createSetup(selectedBaseId, [collection.id])}
              className="rounded-lg bg-brand-600 px-3 py-1.5 text-xs font-medium text-white transition-colors hover:bg-brand-700 disabled:opacity-50"
            >
              Create setup with this pack
            </button>
            <button
              type="button"
              onClick={() => setPairingOpen(false)}
              className="rounded-lg px-3 py-1.5 text-xs text-muted-foreground hover:text-foreground"
            >
              Cancel
            </button>
          </div>
        </div>
      )}

      {error && <p className="text-xs text-destructive">{error}</p>}
    </div>
  );
}
