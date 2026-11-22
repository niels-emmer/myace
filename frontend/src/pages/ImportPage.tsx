import { useState } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { useNavigate, useSearchParams } from 'react-router-dom';
import {
  Upload,
  FolderOpen,
  Scan,
  CheckSquare,
  Square,
  Globe,
  Folder,
  HardDrive,
  Loader2,
  FilePlus2,
} from 'lucide-react';
import { COMPANION_URLS, LocalCompanionSetup, useCompanionHealth } from '../components/LocalCompanionSetup';

const FRAMEWORKS = [
  { id: 'opencode', label: 'OpenCode', globalPath: '~/.config/opencode' },
  { id: 'claude-code', label: 'Claude Code', globalPath: '~/.claude' },
  { id: 'cursor', label: 'Cursor', globalPath: '~/.cursor' },
];

type SourceType = 'local' | 'git' | 'scratch';

interface Artifact {
  artifact_type: string;
  name: string;
  version: string;
  priority: number;
  target_compatibility: string[];
  tags: string[];
  description: string;
  body: string;
  file_path: string;
  selected: boolean;
}

export default function ImportPage() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const initialSource: SourceType =
    searchParams.get('source') === 'git'
      ? 'git'
      : searchParams.get('source') === 'scratch'
        ? 'scratch'
        : 'local';
  const [sourceType, setSourceType] = useState<SourceType>(initialSource);
  const returnToOnboarding = searchParams.get('return') === 'onboarding';
  const [scratchName, setScratchName] = useState('');
  const [scratchDescription, setScratchDescription] = useState('');
  const [collectionName, setCollectionName] = useState('');
  const [framework, setFramework] = useState('opencode');
  const [scope, setScope] = useState<'global' | 'project'>('global');
  const [sourcePath, setSourcePath] = useState('');
  const [gitUrl, setGitUrl] = useState('');
  const [gitBranch, setGitBranch] = useState('main');
  const [gitSubdirectory, setGitSubdirectory] = useState('');
  const [artifacts, setArtifacts] = useState<Artifact[]>([]);
  const [scanned, setScanned] = useState(false);

  const sourceLabel = sourceType === 'git' ? gitUrl : sourcePath;

  // The local companion server (`myace serve`) is what actually scans this
  // machine — the browser has no filesystem access of its own, and the
  // backend's local-scan path only ever sees whatever machine *it* runs on
  // (the server, not a remote visitor's laptop). Poll while "Local Machine"
  // is selected so starting `myace serve` mid-session is picked up live.
  const companionQuery = useCompanionHealth(sourceType === 'local');
  const companionReady = sourceType === 'local' && companionQuery.isSuccess;

  const canScan =
    sourceType === 'git' ? !!gitUrl : !!sourcePath && companionReady;

  // Pre-populate path when framework or scope changes
  const updatePath = (fw: string, sc: 'global' | 'project') => {
    const fwInfo = FRAMEWORKS.find((f) => f.id === fw);
    if (sc === 'global' && fwInfo) {
      setSourcePath(fwInfo.globalPath);
    }
    // For project scope, keep whatever the user typed
  };

  const handleFrameworkChange = (fw: string) => {
    setFramework(fw);
    updatePath(fw, scope);
  };

  const handleScopeChange = (sc: 'global' | 'project') => {
    setScope(sc);
    updatePath(framework, sc);
  };

  // Scan mutation — local machine goes through the companion server running
  // on the user's own device; only Git repos hit the backend directly.
  const scanMutation = useMutation({
    mutationFn: async () => {
      if (sourceType === 'local') {
        if (!companionReady) {
          throw new Error('Local scanner not detected. Follow the setup steps below.');
        }
        const res = await fetch(`${companionQuery.data?.baseUrl ?? COMPANION_URLS[0]}/scan`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json', 'X-MyACE-Companion': '1' },
          body: JSON.stringify({ path: sourcePath, framework }),
        });
        if (!res.ok) {
          const err = await res.json().catch(() => ({ detail: res.statusText }));
          throw new Error(err.detail || 'Scan failed');
        }
        return res.json();
      }

      const res = await fetch('/api/v1/collections/scan', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'same-origin',
        body: JSON.stringify({
          source_type: 'git',
          git_url: gitUrl,
          git_branch: gitBranch || 'main',
          subdirectory: gitSubdirectory,
          framework,
        }),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: res.statusText }));
        throw new Error(err.detail || 'Scan failed');
      }
      return res.json();
    },
    onSuccess: (data) => {
      setArtifacts(
        (data.artifacts || []).map((a: Omit<Artifact, 'selected'>) => ({ ...a, selected: true }))
      );
      setScanned(true);
    },
  });

  const afterPackCreated = (collectionId: string) => {
    queryClient.invalidateQueries({ queryKey: ['collections'] });
    navigate(
      returnToOnboarding
        ? `/onboarding?step=3&pack=${collectionId}`
        : `/packs/${collectionId}`,
    );
  };

  // "Start from scratch" creates an empty pack and hands it to the same
  // pack/editor surfaces as an import.
  const scratchMutation = useMutation({
    mutationFn: async () => {
      const res = await fetch('/api/v1/collections', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'same-origin',
        body: JSON.stringify({
          name: scratchName.trim(),
          description: scratchDescription.trim() || undefined,
          git_url: '',
          collection_type: 'base',
          visibility: 'private',
        }),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: res.statusText }));
        throw new Error(err.detail || 'Could not create the pack');
      }
      return res.json();
    },
    onSuccess: (collection: { id: string }) => afterPackCreated(collection.id),
  });

  // Import mutation
  const importMutation = useMutation({
    mutationFn: async () => {
      const selected = artifacts.filter((a) => a.selected);
      const res = await fetch('/api/v1/collections/import', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'same-origin',
        body: JSON.stringify({
          collection_name: collectionName || `imported-${framework}`,
          collection_description: `Imported from ${sourceLabel}`,
          collection_type: 'base',
          visibility: 'private',
          git_url: sourceType === 'git' ? gitUrl : '',
          artifacts: selected.map(({ selected, ...rest }) => rest),
        }),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: res.statusText }));
        throw new Error(err.detail || 'Import failed');
      }
      return res.json();
    },
    onSuccess: (data: { collection_id: string; collection_name: string }) => {
      afterPackCreated(data.collection_id);
    },
  });

  const toggleAll = () => {
    const allSelected = artifacts.every((a) => a.selected);
    setArtifacts(artifacts.map((a) => ({ ...a, selected: !allSelected })));
  };

  const toggleArtifact = (index: number) => {
    setArtifacts(
      artifacts.map((a, i) => (i === index ? { ...a, selected: !a.selected } : a))
    );
  };

  const typeColors: Record<string, string> = {
    rule: 'bg-blue-50 text-blue-700',
    skill: 'bg-green-50 text-green-700',
    agent: 'bg-purple-50 text-purple-700',
    workflow: 'bg-amber-50 text-amber-700',
    model_config: 'bg-rose-50 text-rose-700',
  };

  const selectedCount = artifacts.filter((a) => a.selected).length;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-foreground">Import packs</h1>
        <p className="text-muted-foreground mt-1">
          Bring in an existing pack from your machine or a repository, or start an empty
          one — then pick which items to keep.
        </p>
      </div>

      {/* Source cards — three ways to acquire a pack */}
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
        {[
          {
            id: 'local' as const,
            icon: HardDrive,
            title: 'This machine',
            description: 'Scan your existing framework configs with the local companion.',
          },
          {
            id: 'git' as const,
            icon: Globe,
            title: 'GitHub repository',
            description: 'Import from a public repo the server can reach.',
          },
          {
            id: 'scratch' as const,
            icon: FilePlus2,
            title: 'Start from scratch',
            description: 'Create a new, empty pack and add items yourself.',
          },
        ].map((card) => {
          const Icon = card.icon;
          const selected = sourceType === card.id;
          return (
            <button
              key={card.id}
              type="button"
              aria-pressed={selected}
              onClick={() => setSourceType(card.id)}
              className={`rounded-xl border p-4 text-left transition-colors ${
                selected
                  ? 'border-brand-500 bg-brand-50'
                  : 'border-border bg-card hover:border-input'
              }`}
            >
              <span
                className={`mb-2 flex h-9 w-9 items-center justify-center rounded-lg ${
                  selected ? 'bg-brand-100 text-brand-700' : 'bg-muted text-muted-foreground'
                }`}
              >
                <Icon className="h-4 w-4" />
              </span>
              <span className="block text-sm font-semibold text-foreground">{card.title}</span>
              <span className="mt-0.5 block text-xs text-muted-foreground">
                {card.description}
              </span>
            </button>
          );
        })}
      </div>

      {sourceType === 'scratch' ? (
        <div className="bg-card rounded-xl border border-border p-6 space-y-4">
          <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
            <div>
              <label className="block text-sm font-medium text-foreground mb-1">Pack name</label>
              <input
                type="text"
                value={scratchName}
                onChange={(e) => setScratchName(e.target.value)}
                placeholder="e.g., my-team-conventions"
                className="w-full px-3 py-2 bg-background text-foreground border border-input rounded-lg text-sm focus:ring-2 focus:ring-brand-500 focus:border-brand-500"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-foreground mb-1">
                Description <span className="text-muted-foreground font-normal">(optional)</span>
              </label>
              <input
                type="text"
                value={scratchDescription}
                onChange={(e) => setScratchDescription(e.target.value)}
                placeholder="What this pack is for…"
                className="w-full px-3 py-2 bg-background text-foreground border border-input rounded-lg text-sm focus:ring-2 focus:ring-brand-500 focus:border-brand-500"
              />
            </div>
          </div>
          <div className="flex justify-end gap-3">
            <button
              type="button"
              onClick={() => scratchMutation.mutate()}
              disabled={!scratchName.trim() || scratchMutation.isPending}
              className="flex items-center gap-2 px-4 py-2 bg-brand-600 text-white rounded-lg hover:bg-brand-700 disabled:opacity-50 text-sm font-medium transition-colors"
            >
              {scratchMutation.isPending ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <FilePlus2 className="h-4 w-4" />
              )}
              Create empty pack
            </button>
          </div>
          {scratchMutation.isError && (
            <div className="p-3 bg-destructive/10 border border-destructive/30 rounded-lg text-sm text-destructive">
              {scratchMutation.error.message}
            </div>
          )}
        </div>
      ) : (
      <div className="bg-card rounded-xl border border-border p-6 space-y-4">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {/* Pack name */}
          <div>
            <label className="block text-sm font-medium text-foreground mb-1">
              Pack name
            </label>
            <input
              type="text"
              value={collectionName}
              onChange={(e) => setCollectionName(e.target.value)}
              placeholder="e.g., my-opencode-config"
              className="w-full px-3 py-2 bg-background text-foreground border border-input rounded-lg text-sm focus:ring-2 focus:ring-brand-500 focus:border-brand-500"
            />
          </div>

          {sourceType === 'local' ? (
            <>
              {/* Source Framework */}
              <div>
                <label className="block text-sm font-medium text-foreground mb-1">
                  Source Framework
                </label>
                <select
                  value={framework}
                  onChange={(e) => handleFrameworkChange(e.target.value)}
                  className="w-full px-3 py-2 bg-background text-foreground border border-input rounded-lg text-sm focus:ring-2 focus:ring-brand-500 focus:border-brand-500"
                >
                  {FRAMEWORKS.map((fw) => (
                    <option key={fw.id} value={fw.id}>
                      {fw.label}
                    </option>
                  ))}
                </select>
              </div>

              {/* Scope */}
              <div>
                <label className="block text-sm font-medium text-foreground mb-1">
                  Scope
                </label>
                <div className="flex gap-2">
                  <button
                    type="button"
                    onClick={() => handleScopeChange('global')}
                    className={`flex items-center gap-2 px-4 py-2 rounded-lg border text-sm transition-colors ${
                      scope === 'global'
                        ? 'border-brand-500 bg-brand-50 text-brand-700'
                        : 'border-border hover:border-input'
                    }`}
                  >
                    <Globe className="h-4 w-4" />
                    Global Settings
                  </button>
                  <button
                    type="button"
                    onClick={() => handleScopeChange('project')}
                    className={`flex items-center gap-2 px-4 py-2 rounded-lg border text-sm transition-colors ${
                      scope === 'project'
                        ? 'border-brand-500 bg-brand-50 text-brand-700'
                        : 'border-border hover:border-input'
                    }`}
                  >
                    <Folder className="h-4 w-4" />
                    Project Settings
                  </button>
                </div>
              </div>

              {/* Source Path */}
              <div>
                <label className="block text-sm font-medium text-foreground mb-1">
                  Source Folder
                </label>
                <div className="flex gap-2">
                  <input
                    type="text"
                    value={sourcePath}
                    onChange={(e) => setSourcePath(e.target.value)}
                    placeholder="~/.config/opencode"
                    className="flex-1 px-3 py-2 bg-background text-foreground border border-input rounded-lg text-sm font-mono focus:ring-2 focus:ring-brand-500 focus:border-brand-500"
                  />
                </div>
                <div className="flex items-center gap-2 mt-2">
                  <div
                    className={`h-2 w-2 rounded-full ${companionReady ? 'bg-green-400' : 'bg-muted-foreground/30'}`}
                  />
                  <span className="text-xs text-muted-foreground">
                    {companionReady
                      ? 'Local scanner detected — ready to scan this machine.'
                      : 'Local scanner not detected. See setup steps below.'}
                  </span>
                </div>
              </div>
            </>
          ) : (
            <>
              {/* Repository URL */}
              <div>
                <label className="block text-sm font-medium text-foreground mb-1">
                  Repository URL
                </label>
                <input
                  type="text"
                  value={gitUrl}
                  onChange={(e) => setGitUrl(e.target.value)}
                  placeholder="https://github.com/owner/repo"
                  className="w-full px-3 py-2 bg-background text-foreground border border-input rounded-lg text-sm font-mono focus:ring-2 focus:ring-brand-500 focus:border-brand-500"
                />
              </div>

              {/* Branch */}
              <div>
                <label className="block text-sm font-medium text-foreground mb-1">
                  Branch
                </label>
                <input
                  type="text"
                  value={gitBranch}
                  onChange={(e) => setGitBranch(e.target.value)}
                  placeholder="main"
                  className="w-full px-3 py-2 bg-background text-foreground border border-input rounded-lg text-sm font-mono focus:ring-2 focus:ring-brand-500 focus:border-brand-500"
                />
              </div>

              {/* Subdirectory */}
              <div>
                <label className="block text-sm font-medium text-foreground mb-1">
                  Subdirectory <span className="text-muted-foreground font-normal">(optional)</span>
                </label>
                <input
                  type="text"
                  value={gitSubdirectory}
                  onChange={(e) => setGitSubdirectory(e.target.value)}
                  placeholder="Leave blank to scan the repository root"
                  className="w-full px-3 py-2 bg-background text-foreground border border-input rounded-lg text-sm font-mono focus:ring-2 focus:ring-brand-500 focus:border-brand-500"
                />
              </div>
            </>
          )}
        </div>

        {sourceType === 'git' && (
          <p className="text-xs text-muted-foreground">
            Only public repositories work out of the box. For a private repo, embed a token in the URL:{' '}
            <code className="bg-muted px-1 rounded">https://&lt;token&gt;@github.com/owner/repo.git</code>
          </p>
        )}

        {/* Scan Button */}
        <div className="flex justify-end">
          <button
            onClick={() => scanMutation.mutate()}
            disabled={!canScan || scanMutation.isPending}
            className="flex items-center gap-2 px-4 py-2 bg-brand-600 text-white rounded-lg hover:bg-brand-700 disabled:opacity-50 text-sm font-medium transition-colors"
          >
            {scanMutation.isPending ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <Scan className="h-4 w-4" />
            )}
            Scan Resources
          </button>
        </div>

        {/* Scan Error */}
        {scanMutation.isError && (
          <div className="p-3 bg-destructive/10 border border-destructive/30 rounded-lg text-sm text-destructive">
            Scan failed: {scanMutation.error.message}
          </div>
        )}

        {/* Local companion setup — shown proactively, not just after a failed scan */}
        {sourceType === 'local' && !companionReady && (
          <LocalCompanionSetup
            sourcePath={sourcePath}
            collectionName={collectionName || `imported-${framework}`}
          />
        )}
      </div>

      )}

      {/* Scan Results */}
      {scanned && artifacts.length > 0 && (
        <div className="bg-card rounded-xl border border-border overflow-hidden">
          <div className="px-6 py-4 border-b border-border flex items-center justify-between">
            <div className="flex items-center gap-3">
              <h2 className="text-lg font-semibold text-card-foreground">
                Discovered Resources
              </h2>
              <span className="text-sm text-muted-foreground">
                ({selectedCount}/{artifacts.length} selected)
              </span>
            </div>
            <button
              onClick={toggleAll}
              className="flex items-center gap-1.5 px-3 py-1.5 text-sm text-muted-foreground hover:text-accent-foreground hover:bg-accent rounded-lg transition-colors"
            >
              {artifacts.every((a) => a.selected) ? (
                <Square className="h-4 w-4" />
              ) : (
                <CheckSquare className="h-4 w-4" />
              )}
              {artifacts.every((a) => a.selected) ? 'Deselect All' : 'Select All'}
            </button>
          </div>

          <div className="divide-y divide-border max-h-96 overflow-y-auto">
            {artifacts.map((artifact, index) => (
              <div
                key={`${artifact.artifact_type}-${artifact.name}-${index}`}
                className={`flex items-center gap-3 px-6 py-3 hover:bg-accent transition-colors cursor-pointer ${
                  artifact.selected ? '' : 'opacity-50'
                }`}
                onClick={() => toggleArtifact(index)}
              >
                <div className="flex-shrink-0">
                  {artifact.selected ? (
                    <CheckSquare className="h-5 w-5 text-brand-600" />
                  ) : (
                    <Square className="h-5 w-5 text-muted-foreground" />
                  )}
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-medium text-card-foreground truncate">
                      {artifact.name}
                    </span>
                    <span
                      className={`px-1.5 py-0.5 rounded text-xs font-medium ${
                        typeColors[artifact.artifact_type] || 'bg-muted text-muted-foreground'
                      }`}
                    >
                      {artifact.artifact_type}
                    </span>
                  </div>
                  <p className="text-xs text-muted-foreground truncate mt-0.5">
                    {artifact.description || artifact.file_path}
                  </p>
                </div>
                <div className="flex-shrink-0 text-xs text-muted-foreground">
                  p{artifact.priority}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {scanned && artifacts.length === 0 && (
        <div className="bg-card rounded-xl border border-border p-12 text-center">
          <FolderOpen className="h-12 w-12 text-muted-foreground mx-auto mb-3" />
          <p className="text-muted-foreground">No items found at the specified source.</p>
          <p className="text-xs text-muted-foreground/60 mt-1">
            Make sure it contains skills/, agents/, commands/, or AGENTS.md
          </p>
        </div>
      )}

      {/* Import Button + CLI Command */}
      {scanned && selectedCount > 0 && (
        <div className="space-y-4">
          <div className="flex justify-end">
            <button
              onClick={() => importMutation.mutate()}
              disabled={importMutation.isPending}
              className="flex items-center gap-2 px-6 py-2.5 bg-brand-600 text-white rounded-lg hover:bg-brand-700 disabled:opacity-50 text-sm font-medium transition-colors"
            >
              {importMutation.isPending ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <Upload className="h-4 w-4" />
              )}
              Import {selectedCount} Resource{selectedCount !== 1 ? 's' : ''} from{' '}
              {sourceType === 'git' ? 'GitHub' : 'Local System'}
            </button>
          </div>

          {/* Import Error */}
          {importMutation.isError && (
            <div className="p-3 bg-destructive/10 border border-destructive/30 rounded-lg text-sm text-destructive">
              Import failed: {importMutation.error.message}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

