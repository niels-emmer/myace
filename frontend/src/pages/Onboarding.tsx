import { useEffect, useMemo, useState } from 'react';
import { Link, useNavigate, useSearchParams } from 'react-router-dom';
import { useQueries, useQuery, useQueryClient } from '@tanstack/react-query';
import {
  ArrowRight,
  Check,
  Download,
  FolderGit2,
  Loader2,
  Sparkles,
} from 'lucide-react';
import { adaptersApi, collectionsApi } from '../lib/api';
import {
  clearDraft,
  companionApi,
  draftToProfileCreate,
  fetchCompanionHealth,
  loadDraft,
  onboardingApi,
  resolveInitialDraft,
  saveDraft,
  setupProfilesApi,
} from '../lib/setupApi';
import { BUNDLES } from '../lib/bundles';
import { frameworkLabel, packKindLabel } from '../lib/packs';
import { useAuth } from '../contexts/AuthContext';
import { resolveInstallPath, supportsMachineInstall } from '../types/setup';
import type {
  InstallLocation,
  OnboardingDraft,
} from '../types/setup';
import type { ArtifactType, Collection } from '../types';
import InstallMethodPanel from '../components/InstallMethodPanel';

const STEP_LABELS = ['Frameworks', 'Packs', 'Review', 'Location', 'Install'];

const TYPE_ORDER: ArtifactType[] = ['rule', 'workflow', 'agent', 'skill', 'model_config'];

function defaultLocation(target: string, projectRoot: string | undefined): InstallLocation {
  if (projectRoot) return 'project';
  return supportsMachineInstall(target) ? 'machine' : 'project';
}

export default function Onboarding() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [searchParams, setSearchParams] = useSearchParams();
  const { refresh } = useAuth();

  const [draft, setDraft] = useState<OnboardingDraft>(() =>
    resolveInitialDraft(searchParams, loadDraft()),
  );
  const [pairingAddOnId, setPairingAddOnId] = useState<string | null>(null);
  const [pairingBaseId, setPairingBaseId] = useState('');
  const [installTarget, setInstallTarget] = useState('');
  const [creating, setCreating] = useState(false);
  const [finishing, setFinishing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [autoSelectedDetected, setAutoSelectedDetected] = useState(false);

  const { data: adapters } = useQuery({
    queryKey: ['adapters'],
    queryFn: () => adaptersApi.list(),
  });

  const { data: collections } = useQuery({
    queryKey: ['collections'],
    queryFn: () => collectionsApi.list(),
  });

  // The companion is optional. Only used to preselect frameworks (audit) and
  // to offer direct install (apply capability). Never blocks a step.
  const companion = useQuery({
    queryKey: ['companion-health-apply'],
    queryFn: fetchCompanionHealth,
    retry: 1,
    staleTime: 15_000,
    refetchInterval: 30_000,
  });
  const audit = useQuery({
    queryKey: ['companion-audit', companion.data?.baseUrl],
    queryFn: () => companionApi.auditHome(companion.data!.baseUrl),
    enabled: Boolean(companion.data?.baseUrl),
    retry: 1,
    staleTime: 60_000,
  });

  const enabledAdapters = useMemo(
    () => (adapters ?? []).filter((adapter) => adapter.enabled).map((adapter) => adapter.name),
    [adapters],
  );

  const basePacks = useMemo(
    () => (collections ?? []).filter((collection) => collection.collection_type === 'base'),
    [collections],
  );
  const addOnPacks = useMemo(
    () => (collections ?? []).filter((collection) => collection.collection_type === 'additional'),
    [collections],
  );
  const collectionById = useMemo(
    () => new Map((collections ?? []).map((collection) => [collection.id, collection])),
    [collections],
  );

  // Persist the draft on every change; localStorage is a convenience only.
  useEffect(() => {
    saveDraft(draft);
  }, [draft]);

  const enabledAdapterSet = useMemo(() => new Set(enabledAdapters), [enabledAdapters]);

  // Preselect frameworks the companion found, once. A resumed draft (or any
  // manual selection) always wins. This is a render-phase update (the pattern
  // Layout.tsx/CommandPalette.tsx use) rather than an effect, so the selection
  // is present on the first paint after the audit resolves.
  if (!autoSelectedDetected && draft.frameworks.length === 0 && audit.data) {
    const detected = Object.entries(audit.data.targets)
      .filter(([, target]) => target.detected)
      .map(([name]) => name)
      .filter((name) => enabledAdapterSet.has(name));
    if (detected.length > 0) {
      setAutoSelectedDetected(true);
      setDraft({ ...draft, frameworks: detected });
    }
  }

  // `?pack=` may name an add-on. Never invent a base: clamp to step 2 and show
  // the pairing prompt instead of silently accepting the add-on as a base.
  const selectedBasePack = draft.basePackId ? collectionById.get(draft.basePackId) : undefined;
  const pendingPairingPack =
    (pairingAddOnId ? collectionById.get(pairingAddOnId) : undefined) ??
    (selectedBasePack?.collection_type === 'additional' ? selectedBasePack : undefined);
  const effectiveStep = pendingPairingPack && draft.step > 2 ? 2 : draft.step;
  const selectedInstallTarget =
    installTarget && draft.frameworks.includes(installTarget)
      ? installTarget
      : (draft.frameworks[0] ?? '');

  const goToStep = (step: number, overrides: Partial<OnboardingDraft> = {}) => {
    const next = { ...draft, ...overrides, step };
    setDraft(next);
    const params: Record<string, string> = { step: String(step) };
    if (next.basePackId) params.pack = next.basePackId;
    setSearchParams(params, { replace: true });
    window.scrollTo?.({ top: 0 });
  };

  const selectedCollections = useMemo(() => {
    const ids = [draft.basePackId, ...draft.addOnPackIds].filter(
      (id): id is string => Boolean(id),
    );
    return ids
      .map((id) => collectionById.get(id))
      .filter((collection): collection is Collection => Boolean(collection));
  }, [draft.basePackId, draft.addOnPackIds, collectionById]);

  const itemQueries = useQueries({
    queries: selectedCollections.map((collection) => ({
      queryKey: ['artifacts', collection.id, { include_disabled: false }],
      queryFn: () => collectionsApi.getArtifacts(collection.id),
      enabled: effectiveStep === 3 || effectiveStep === 5,
    })),
  });
  const itemsLoading = itemQueries.some((query) => query.isLoading);
  const itemCounts: Partial<Record<ArtifactType, number>> = {};
  const seenItems = new Map<string, ArtifactType>();
  for (const query of itemQueries) {
    for (const artifact of query.data ?? []) {
      seenItems.set(artifact.name, artifact.artifact_type);
    }
  }
  for (const type of seenItems.values()) {
    itemCounts[type] = (itemCounts[type] ?? 0) + 1;
  }
  const totalItems = seenItems.size;

  const mostUsedBase = useMemo(
    () =>
      [...basePacks].sort(
        (a, b) => (b.download_count ?? 0) - (a.download_count ?? 0),
      )[0] ?? null,
    [basePacks],
  );

  const pairingBaseSelection = pairingBaseId || mostUsedBase?.id || '';

  const hasBasePack = selectedBasePack?.collection_type === 'base';
  const stepValid = (() => {
    if (effectiveStep === 1) return draft.frameworks.length > 0;
    if (effectiveStep === 2) return hasBasePack;
    if (effectiveStep === 3) return Boolean(hasBasePack && draft.name.trim());
    if (effectiveStep === 4) return draft.frameworks.length > 0;
    return Boolean(draft.profileId);
  })();

  const handleNext = async () => {
    if (effectiveStep < 4) {
      goToStep(effectiveStep + 1);
      return;
    }
    if (effectiveStep === 4) {
      if (!draft.basePackId) return;
      setCreating(true);
      setError(null);
      try {
        const payload = draftToProfileCreate(draft, {
          baseCollectionId: draft.basePackId,
          additionalCollectionIds: draft.addOnPackIds,
        });
        const saved = draft.profileId
          ? await setupProfilesApi.update(draft.profileId, payload)
          : await setupProfilesApi.create(payload);
        queryClient.invalidateQueries({ queryKey: ['profiles'] });
        goToStep(5, {
          profileId: saved.id,
          claimedTargets:
            saved.id === draft.profileId ? draft.claimedTargets : [],
        });
      } catch (err) {
        setError((err as Error).message);
      } finally {
        setCreating(false);
      }
      return;
    }
    await finish(false);
  };

  const finish = async (skip: boolean) => {
    setFinishing(true);
    setError(null);
    try {
      await onboardingApi.setCompleted(true);
      clearDraft();
      await refresh();
      queryClient.invalidateQueries({ queryKey: ['profiles'] });
      navigate(!skip && draft.profileId ? `/setups/${draft.profileId}` : '/');
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setFinishing(false);
    }
  };

  const selectBundle = (bundleId: string) => {
    const bundle = BUNDLES.find((entry) => entry.id === bundleId);
    if (!bundle) return;
    const base = basePacks.find((pack) => pack.name === bundle.basePackName);
    if (!base) return;
    const addOnIds = addOnPacks
      .filter((pack) => bundle.addOnPackNames.includes(pack.name))
      .map((pack) => pack.id);
    setDraft((current) => ({
      ...current,
      bundleId: bundle.id,
      basePackId: base.id,
      addOnPackIds: addOnIds,
    }));
    setPairingAddOnId(null);
  };

  const toggleAddOn = (packId: string) => {
    if (draft.addOnPackIds.includes(packId)) {
      setDraft((current) => ({
        ...current,
        bundleId: null,
        addOnPackIds: current.addOnPackIds.filter((id) => id !== packId),
      }));
      return;
    }
    if (!draft.basePackId) {
      setPairingAddOnId(packId);
      setPairingBaseId(mostUsedBase?.id ?? '');
      return;
    }
    setDraft((current) => ({
      ...current,
      bundleId: null,
      addOnPackIds: [...current.addOnPackIds, packId],
    }));
  };

  const confirmPairing = () => {
    if (!pendingPairingPack || !pairingBaseSelection) return;
    setDraft((current) => ({
      ...current,
      bundleId: null,
      basePackId: pairingBaseSelection,
      addOnPackIds: [...new Set([...current.addOnPackIds, pendingPairingPack.id])],
    }));
    setPairingAddOnId(null);
    setPairingBaseId('');
  };

  const cancelPairing = () => {
    setPairingAddOnId(null);
    if (selectedBasePack?.collection_type === 'additional') {
      setDraft((current) => ({ ...current, basePackId: null }));
    }
  };

  const toggleFramework = (name: string) => {
    setDraft((current) => ({
      ...current,
      frameworks: current.frameworks.includes(name)
        ? current.frameworks.filter((framework) => framework !== name)
        : [...current.frameworks, name],
    }));
  };

  const setLocation = (target: string, location: InstallLocation) => {
    setDraft((current) => ({
      ...current,
      locations: { ...current.locations, [target]: location },
    }));
  };

  const selectedInstallLocation: InstallLocation =
    draft.locations[selectedInstallTarget] ??
    defaultLocation(selectedInstallTarget, companion.data?.project_root);

  return (
    <div className="mx-auto max-w-4xl space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Sparkles className="h-5 w-5 text-brand-600" />
          <h1 className="text-xl font-bold text-foreground">Set up MyACE</h1>
        </div>
        <div className="flex items-center gap-4">
          <span className="text-sm text-muted-foreground">
            Step <span className="font-semibold text-foreground">{effectiveStep}</span> of 5
          </span>
          <button
            type="button"
            onClick={() => finish(true)}
            disabled={finishing}
            className="rounded-lg px-2 py-1 text-sm text-muted-foreground transition-colors hover:text-foreground disabled:opacity-50"
          >
            Skip for now
          </button>
        </div>
      </div>

      {/* Progress */}
      <div className="space-y-2">
        <div className="grid grid-cols-5 gap-2">
          {STEP_LABELS.map((label, index) => (
            <div
              key={label}
              className={`h-1.5 rounded-full ${
                index < effectiveStep ? 'bg-brand-500' : 'bg-muted'
              }`}
            />
          ))}
        </div>
        <div className="grid grid-cols-5 gap-2 text-center text-[11px] text-muted-foreground">
          {STEP_LABELS.map((label) => (
            <span key={label}>{label}</span>
          ))}
        </div>
      </div>

      {error && (
        <div className="rounded-lg border border-destructive/30 bg-destructive/10 p-3 text-sm text-destructive">
          {error}
        </div>
      )}

      <div className="rounded-xl border border-border bg-card p-6">
        {/* Step 1 — frameworks */}
        {effectiveStep === 1 && (
          <div className="space-y-4">
            <div>
              <h2 className="text-lg font-semibold text-foreground">What do you use?</h2>
              <p className="mt-1 text-sm text-muted-foreground">
                Pick every framework you want this setup to work in.
                {audit.data && Object.values(audit.data.targets).some((t) => t.detected)
                  ? ' We detected some on this machine.'
                  : ''}
              </p>
            </div>
            <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
              {enabledAdapters.map((name) => {
                const selected = draft.frameworks.includes(name);
                const detected = Boolean(audit.data?.targets[name]?.detected);
                return (
                  <button
                    key={name}
                    type="button"
                    aria-pressed={selected}
                    onClick={() => toggleFramework(name)}
                    className={`rounded-lg border px-4 py-3 text-left transition-colors ${
                      selected
                        ? 'border-brand-500 bg-brand-50 text-brand-700'
                        : 'border-border text-foreground hover:border-input'
                    }`}
                  >
                    <span className="flex items-center gap-2 text-sm font-medium">
                      {selected && <Check className="h-4 w-4" />}
                      {frameworkLabel(name)}
                    </span>
                    <span className="block text-xs text-muted-foreground">
                      {resolveInstallPath(name, 'machine')}
                      {detected ? ' · detected on this machine' : ''}
                    </span>
                  </button>
                );
              })}
            </div>
            {enabledAdapters.length === 0 && (
              <p className="text-sm text-muted-foreground">
                No adapters are enabled. An admin can enable one under Settings → System.
              </p>
            )}
            <p className="text-xs text-muted-foreground">
              Not sure? Start with any one framework. You can add or remove frameworks
              later under Advanced on your setup page.
            </p>
          </div>
        )}

        {/* Step 2 — packs */}
        {effectiveStep === 2 && (
          <div className="space-y-5">
            <div>
              <h2 className="text-lg font-semibold text-foreground">
                What should your agent know?
              </h2>
              <p className="mt-1 text-sm text-muted-foreground">
                Pick a starting point and any add-ons. Everything can be customized later.
              </p>
              <p className="mt-2 text-sm text-muted-foreground">
                Already have configs you like?{' '}
                <Link
                  to="/packs/import?return=onboarding"
                  className="font-medium text-brand-600 hover:underline"
                >
                  Import them instead →
                </Link>
              </p>
            </div>

            {pendingPairingPack && (
              <div className="space-y-3 rounded-lg border border-brand-200 bg-brand-50 p-4">
                <p className="text-sm font-medium text-brand-900">
                  Pair “{pendingPairingPack.name}” with a starting point
                </p>
                <p className="text-xs text-brand-800">
                  {packKindLabel(pendingPairingPack.collection_type)} packs layer onto a
                  complete baseline. Choose which one.
                </p>
                <div className="space-y-2">
                  {[...basePacks]
                    .sort((a, b) => (b.download_count ?? 0) - (a.download_count ?? 0))
                    .map((pack) => (
                      <label
                        key={pack.id}
                        className="flex items-center gap-2 rounded border border-brand-200 bg-card px-3 py-2 text-sm"
                      >
                        <input
                          type="radio"
                          name="pairing-base"
                          value={pack.id}
                          checked={pairingBaseSelection === pack.id}
                          onChange={() => setPairingBaseId(pack.id)}
                        />
                        <span className="font-medium text-foreground">{pack.name}</span>
                        <span className="ml-auto text-xs text-muted-foreground">
                          {pack.artifact_count} items
                        </span>
                      </label>
                    ))}
                </div>
                <div className="flex gap-2">
                  <button
                    type="button"
                    onClick={confirmPairing}
                    disabled={!pairingBaseSelection}
                    className="rounded-lg bg-brand-600 px-3 py-1.5 text-sm font-medium text-white transition-colors hover:bg-brand-700 disabled:opacity-50"
                  >
                    Use this starting point
                  </button>
                  <button
                    type="button"
                    onClick={cancelPairing}
                    className="rounded-lg px-3 py-1.5 text-sm text-muted-foreground hover:text-foreground"
                  >
                    Cancel
                  </button>
                </div>
              </div>
            )}

            <div>
              <div className="mb-2 flex items-center justify-between">
                <h3 className="text-sm font-medium text-foreground">Starting points</h3>
                <Link to="/packs" className="text-sm text-brand-600 hover:underline">
                  Browse all packs
                </Link>
              </div>
              <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
                {BUNDLES.map((bundle) => {
                  const base = basePacks.find((pack) => pack.name === bundle.basePackName);
                  const selected = bundle.id === draft.bundleId;
                  return (
                    <button
                      key={bundle.id}
                      type="button"
                      disabled={!base}
                      aria-pressed={selected}
                      onClick={() => selectBundle(bundle.id)}
                      className={`rounded-lg border px-4 py-3 text-left transition-colors ${
                        selected
                          ? 'border-brand-500 bg-brand-50 text-brand-700'
                          : 'border-border text-foreground hover:border-input'
                      } disabled:cursor-not-allowed disabled:opacity-50`}
                    >
                      <span className="flex items-center gap-2 text-sm font-medium">
                        {selected && <Check className="h-4 w-4" />}
                        {bundle.name}
                      </span>
                      <span className="mt-0.5 block text-xs text-muted-foreground">
                        {bundle.description}
                      </span>
                      <span className="mt-1 block text-xs text-muted-foreground">
                        {base ? `${base.artifact_count} items` : 'Starter pack unavailable'}
                      </span>
                    </button>
                  );
                })}
              </div>
            </div>

            {addOnPacks.length > 0 && (
              <div>
                <h3 className="mb-2 text-sm font-medium text-foreground">Add-ons</h3>
                <div className="flex flex-wrap gap-2">
                  {addOnPacks.map((pack) => {
                    const selected = draft.addOnPackIds.includes(pack.id);
                    return (
                      <button
                        key={pack.id}
                        type="button"
                        aria-pressed={selected}
                        onClick={() => toggleAddOn(pack.id)}
                        className={`rounded-lg border px-3 py-2 text-left text-sm transition-colors ${
                          selected
                            ? 'border-purple-500 bg-purple-50 text-purple-700'
                            : 'border-border text-foreground hover:border-input'
                        }`}
                      >
                        <span className="flex items-center gap-1.5 font-medium">
                          {selected && <Check className="h-3.5 w-3.5" />}
                          {pack.name}
                        </span>
                        <span className="block text-xs text-muted-foreground">
                          {pack.artifact_count} items
                        </span>
                      </button>
                    );
                  })}
                </div>
              </div>
            )}
          </div>
        )}

        {/* Step 3 — review + name */}
        {effectiveStep === 3 && (
          <div className="space-y-4">
            <div>
              <h2 className="text-lg font-semibold text-foreground">Review your setup</h2>
              <p className="mt-1 text-sm text-muted-foreground">
                One starting point plus add-ons. Individual items stay editable on the setup
                page.
              </p>
            </div>

            <div className="overflow-hidden rounded-lg border border-border">
              {selectedCollections.map((pack) => (
                <div
                  key={pack.id}
                  className="flex items-center gap-2 border-b border-border px-4 py-3 last:border-b-0"
                >
                  <span
                    className={`rounded px-2 py-0.5 text-xs font-medium ${
                      pack.collection_type === 'base'
                        ? 'bg-blue-50 text-blue-700'
                        : 'bg-purple-50 text-purple-700'
                    }`}
                  >
                    {packKindLabel(pack.collection_type)}
                  </span>
                  <span className="text-sm font-medium text-foreground">{pack.name}</span>
                  <span className="ml-auto text-xs text-muted-foreground">
                    {pack.artifact_count} items
                  </span>
                </div>
              ))}
              {selectedCollections.length === 0 && (
                <p className="px-4 py-3 text-sm text-muted-foreground">No packs selected.</p>
              )}
            </div>

            <p className="text-xs text-muted-foreground">
              {itemsLoading
                ? 'Counting items…'
                : `${totalItems} items total · ${TYPE_ORDER.filter((type) => itemCounts[type])
                    .map((type) => `${itemCounts[type]} ${type}`)
                    .join(', ')}`}
            </p>

            <details className="rounded-lg border border-border">
              <summary className="cursor-pointer px-4 py-3 text-sm text-muted-foreground">
                Customize items
              </summary>
              <p className="px-4 pb-3 text-xs text-muted-foreground">
                Item toggles live on the setup page after creation, so nothing is hidden from
                you here. You can disable individual rules, skills, and agents there at any
                time.
              </p>
            </details>

            <div className="space-y-3">
              <div>
                <label htmlFor="setup-name" className="mb-1 block text-sm font-medium text-foreground">
                  Setup name
                </label>
                <input
                  id="setup-name"
                  type="text"
                  value={draft.name}
                  onChange={(event) =>
                    setDraft((current) => ({ ...current, name: event.target.value }))
                  }
                  className="w-full rounded-lg border border-input bg-background px-3 py-2 text-sm text-foreground"
                />
              </div>
              <div>
                <label
                  htmlFor="setup-description"
                  className="mb-1 block text-sm font-medium text-foreground"
                >
                  Description <span className="font-normal text-muted-foreground">(optional)</span>
                </label>
                <input
                  id="setup-description"
                  type="text"
                  value={draft.description}
                  onChange={(event) =>
                    setDraft((current) => ({ ...current, description: event.target.value }))
                  }
                  placeholder="What this setup is for…"
                  className="w-full rounded-lg border border-input bg-background px-3 py-2 text-sm text-foreground"
                />
              </div>
            </div>
          </div>
        )}

        {/* Step 4 — location */}
        {effectiveStep === 4 && (
          <div className="space-y-4">
            <div>
              <h2 className="text-lg font-semibold text-foreground">Where should it go?</h2>
              <p className="mt-1 text-sm text-muted-foreground">
                Project installs live in that repository. Machine installs apply everywhere.
              </p>
            </div>
            <div className="overflow-x-auto rounded-lg border border-border">
              <table className="w-full text-sm">
                <thead className="border-b border-border bg-muted/50 text-left text-xs text-muted-foreground">
                  <tr>
                    <th className="px-4 py-2 font-medium">Framework</th>
                    <th className="px-4 py-2 font-medium">Location</th>
                    <th className="px-4 py-2 font-medium">Resolves to</th>
                  </tr>
                </thead>
                <tbody>
                  {draft.frameworks.map((framework) => {
                    const location =
                      draft.locations[framework] ??
                      defaultLocation(framework, companion.data?.project_root);
                    const machineSupported = supportsMachineInstall(framework);
                    return (
                      <tr key={framework} className="border-b border-border last:border-b-0">
                        <td className="px-4 py-3 font-medium text-foreground">{framework}</td>
                        <td className="px-4 py-3">
                          <div className="flex flex-wrap gap-2">
                            <label className="flex items-center gap-1.5 text-xs">
                              <input
                                type="radio"
                                name={`location-${framework}`}
                                checked={location === 'project'}
                                onChange={() => setLocation(framework, 'project')}
                              />
                              This project
                            </label>
                            <label
                              className={`flex items-center gap-1.5 text-xs ${
                                machineSupported ? '' : 'opacity-50'
                              }`}
                            >
                              <input
                                type="radio"
                                name={`location-${framework}`}
                                checked={location === 'machine'}
                                disabled={!machineSupported}
                                onChange={() => setLocation(framework, 'machine')}
                              />
                              This machine
                            </label>
                          </div>
                        </td>
                        <td className="px-4 py-3 font-mono text-xs text-muted-foreground">
                          {resolveInstallPath(framework, location)}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
            <p className="text-xs text-muted-foreground">
              A project install wins over a machine install for that framework, so this repo can
              differ from your global default.
            </p>
          </div>
        )}

        {/* Step 5 — install */}
        {effectiveStep === 5 && (
          <div className="space-y-5">
            <div>
              <h2 className="text-lg font-semibold text-foreground">Install your setup</h2>
              <p className="mt-1 text-sm text-muted-foreground">
                Pick a method. Nothing is written without your confirmation.
              </p>
            </div>

            {!draft.profileId ? (
              <p className="text-sm text-destructive">
                The setup was not created. Go back and try again.
              </p>
            ) : (
              <>
                <div className="flex flex-wrap gap-2">
                  {draft.frameworks.map((framework) => {
                    const claimed = draft.claimedTargets.includes(framework);
                    return (
                      <button
                        key={framework}
                        type="button"
                        onClick={() => setInstallTarget(framework)}
                        aria-pressed={selectedInstallTarget === framework}
                        className={`rounded-lg border px-3 py-2 text-left text-sm transition-colors ${
                          selectedInstallTarget === framework
                            ? 'border-brand-500 bg-brand-50 text-brand-700'
                            : 'border-border text-foreground hover:border-input'
                        }`}
                      >
                        <span className="block font-medium">{framework}</span>
                        <span className="block text-xs text-muted-foreground">
                          {claimed ? 'Installed, not verified' : 'Not installed'}
                        </span>
                      </button>
                    );
                  })}
                </div>

                {selectedInstallTarget && (
                  <div className="space-y-3">
                    <p className="text-xs text-muted-foreground">
                      Installs to{' '}
                      <span className="font-mono">
                        {resolveInstallPath(selectedInstallTarget, selectedInstallLocation)}
                      </span>
                    </p>
                    <InstallMethodPanel
                      key={`${selectedInstallTarget}:${selectedInstallLocation}`}
                      profileId={draft.profileId}
                      profileName={draft.name.trim() || 'My setup'}
                      target={selectedInstallTarget}
                      location={selectedInstallLocation}
                      compact
                      onClaimed={() => {
                        setDraft((current) => ({
                          ...current,
                          claimedTargets: current.claimedTargets.includes(selectedInstallTarget)
                            ? current.claimedTargets
                            : [...current.claimedTargets, selectedInstallTarget],
                        }));
                      }}
                    />
                  </div>
                )}

                <div className="rounded-lg border border-border bg-muted p-3 text-xs text-muted-foreground">
                  Verify later with <code className="font-mono">myace check --report</code>.
                  Until then we show “installed, not verified” rather than a green check.
                </div>
              </>
            )}
          </div>
        )}

        {/* Footer */}
        <div className="mt-6 flex items-center justify-between border-t border-border pt-4">
          <button
            type="button"
            onClick={() => goToStep(effectiveStep - 1)}
            disabled={effectiveStep === 1}
            className="rounded-lg border border-border px-4 py-2 text-sm text-foreground transition-colors hover:bg-accent disabled:opacity-50"
          >
            Back
          </button>
          <div className="flex items-center gap-3">
            <span className="hidden text-xs text-muted-foreground sm:inline">
              You can change all of this later.
            </span>
            <button
              type="button"
              onClick={handleNext}
              disabled={!stepValid || creating || finishing}
              className="flex items-center gap-2 rounded-lg bg-brand-600 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-brand-700 disabled:opacity-50"
            >
              {creating || finishing ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : effectiveStep === 5 ? (
                <Download className="h-4 w-4" />
              ) : (
                <ArrowRight className="h-4 w-4" />
              )}
              {effectiveStep === 5 ? 'Finish' : 'Continue'}
            </button>
          </div>
        </div>
      </div>

      <p className="flex items-center justify-center gap-2 text-xs text-muted-foreground">
        <FolderGit2 className="h-3.5 w-3.5" />
        A setup is a starting-point pack plus add-ons, installed into every framework you use.
      </p>
    </div>
  );
}
