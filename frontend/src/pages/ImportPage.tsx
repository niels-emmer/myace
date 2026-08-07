import { useState } from 'react';
import { useMutation } from '@tanstack/react-query';
import {
  Upload,
  FolderOpen,
  Scan,
  CheckSquare,
  Square,
  Terminal,
  Globe,
  Folder,
  Copy,
  Check as CheckIcon,
  Loader2,
} from 'lucide-react';

const FRAMEWORKS = [
  { id: 'opencode', label: 'OpenCode', globalPath: '~/.config/opencode' },
  { id: 'claude-code', label: 'Claude Code', globalPath: '~/.claude' },
  { id: 'cursor', label: 'Cursor', globalPath: '~/.cursor' },
];

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
  const [collectionName, setCollectionName] = useState('');
  const [framework, setFramework] = useState('opencode');
  const [scope, setScope] = useState<'global' | 'project'>('global');
  const [sourcePath, setSourcePath] = useState('');
  const [artifacts, setArtifacts] = useState<Artifact[]>([]);
  const [scanned, setScanned] = useState(false);
  const [cliCommand, setCliCommand] = useState('');
  const [copied, setCopied] = useState(false);

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

  // Scan mutation
  const scanMutation = useMutation({
    mutationFn: async () => {
      const res = await fetch('/api/v1/collections/scan', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ path: sourcePath, framework }),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: res.statusText }));
        throw new Error(err.detail || 'Scan failed');
      }
      return res.json();
    },
    onSuccess: (data) => {
      setArtifacts(
        (data.artifacts || []).map((a: any) => ({ ...a, selected: true }))
      );
      setScanned(true);
    },
  });

  // Import mutation
  const importMutation = useMutation({
    mutationFn: async () => {
      const selected = artifacts.filter((a) => a.selected);
      const res = await fetch('/api/v1/collections/import', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          collection_name: collectionName || `imported-${framework}`,
          collection_description: `Imported from ${sourcePath}`,
          collection_type: 'base',
          visibility: 'private',
          owner_email: `import-${Date.now()}@myace.local`,
          artifacts: selected.map(({ selected, ...rest }) => rest),
        }),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: res.statusText }));
        throw new Error(err.detail || 'Import failed');
      }
      return res.json();
    },
    onSuccess: (data) => {
      setCliCommand(
        `myace import --path "${sourcePath}" --name "${data.collection_name}" --push`
      );
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

  const copyToClipboard = async (text: string) => {
    await navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
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
        <h1 className="text-2xl font-bold text-gray-900">Import from Local System</h1>
        <p className="text-gray-500 mt-1">
          Scan an existing local configuration and import it as a MyACE collection
        </p>
      </div>

      {/* Configuration Form */}
      <div className="bg-white rounded-xl border border-gray-200 p-6 space-y-4">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {/* Collection Name */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Collection Name
            </label>
            <input
              type="text"
              value={collectionName}
              onChange={(e) => setCollectionName(e.target.value)}
              placeholder="e.g., my-opencode-config"
              className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-brand-500 focus:border-brand-500"
            />
          </div>

          {/* Source Framework */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Source Framework
            </label>
            <select
              value={framework}
              onChange={(e) => handleFrameworkChange(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-brand-500 focus:border-brand-500"
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
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Scope
            </label>
            <div className="flex gap-2">
              <button
                type="button"
                onClick={() => handleScopeChange('global')}
                className={`flex items-center gap-2 px-4 py-2 rounded-lg border text-sm transition-colors ${
                  scope === 'global'
                    ? 'border-brand-500 bg-brand-50 text-brand-700'
                    : 'border-gray-200 hover:border-gray-300'
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
                    : 'border-gray-200 hover:border-gray-300'
                }`}
              >
                <Folder className="h-4 w-4" />
                Project Settings
              </button>
            </div>
          </div>

          {/* Source Path */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Source Folder
            </label>
            <div className="flex gap-2">
              <input
                type="text"
                value={sourcePath}
                onChange={(e) => setSourcePath(e.target.value)}
                placeholder="~/.config/opencode"
                className="flex-1 px-3 py-2 border border-gray-300 rounded-lg text-sm font-mono focus:ring-2 focus:ring-brand-500 focus:border-brand-500"
              />
            </div>
          </div>
        </div>

        {/* Scan Button */}
        <div className="flex justify-end">
          <button
            onClick={() => scanMutation.mutate()}
            disabled={!sourcePath || scanMutation.isPending}
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
          <div className="p-3 bg-red-50 border border-red-200 rounded-lg text-sm text-red-700">
            Scan failed: {scanMutation.error.message}
            <div className="mt-2 text-xs text-red-500">
              Tip: When running in Docker, paths under{' '}
              <code className="bg-red-100 px-1 rounded">/host-home/</code> are
              accessible. Use the CLI directly for local paths:
            </div>
            <div className="mt-2 flex items-center gap-2 bg-red-100 p-2 rounded">
              <code className="text-xs flex-1">
                myace import --path &quot;{sourcePath}&quot; --name &quot;{collectionName || `imported-${framework}`}&quot;
              </code>
              <button
                onClick={() =>
                  copyToClipboard(
                    `myace import --path "${sourcePath}" --name "${collectionName || `imported-${framework}`}"`
                  )
                }
                className="p-1 hover:bg-red-200 rounded"
              >
                {copied ? (
                  <CheckIcon className="h-3 w-3 text-green-600" />
                ) : (
                  <Copy className="h-3 w-3" />
                )}
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Scan Results */}
      {scanned && artifacts.length > 0 && (
        <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
          <div className="px-6 py-4 border-b border-gray-200 flex items-center justify-between">
            <div className="flex items-center gap-3">
              <h2 className="text-lg font-semibold text-gray-900">
                Discovered Resources
              </h2>
              <span className="text-sm text-gray-500">
                ({selectedCount}/{artifacts.length} selected)
              </span>
            </div>
            <button
              onClick={toggleAll}
              className="flex items-center gap-1.5 px-3 py-1.5 text-sm text-gray-600 hover:text-gray-900 hover:bg-gray-100 rounded-lg transition-colors"
            >
              {artifacts.every((a) => a.selected) ? (
                <Square className="h-4 w-4" />
              ) : (
                <CheckSquare className="h-4 w-4" />
              )}
              {artifacts.every((a) => a.selected) ? 'Deselect All' : 'Select All'}
            </button>
          </div>

          <div className="divide-y divide-gray-100 max-h-96 overflow-y-auto">
            {artifacts.map((artifact, index) => (
              <div
                key={`${artifact.artifact_type}-${artifact.name}-${index}`}
                className={`flex items-center gap-3 px-6 py-3 hover:bg-gray-50 transition-colors cursor-pointer ${
                  artifact.selected ? '' : 'opacity-50'
                }`}
                onClick={() => toggleArtifact(index)}
              >
                <div className="flex-shrink-0">
                  {artifact.selected ? (
                    <CheckSquare className="h-5 w-5 text-brand-600" />
                  ) : (
                    <Square className="h-5 w-5 text-gray-300" />
                  )}
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-medium text-gray-900 truncate">
                      {artifact.name}
                    </span>
                    <span
                      className={`px-1.5 py-0.5 rounded text-xs font-medium ${
                        typeColors[artifact.artifact_type] || 'bg-gray-50 text-gray-600'
                      }`}
                    >
                      {artifact.artifact_type}
                    </span>
                  </div>
                  <p className="text-xs text-gray-500 truncate mt-0.5">
                    {artifact.description || artifact.file_path}
                  </p>
                </div>
                <div className="flex-shrink-0 text-xs text-gray-400">
                  p{artifact.priority}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {scanned && artifacts.length === 0 && (
        <div className="bg-white rounded-xl border border-gray-200 p-12 text-center">
          <FolderOpen className="h-12 w-12 text-gray-300 mx-auto mb-3" />
          <p className="text-gray-500">No artifacts found at the specified path.</p>
          <p className="text-xs text-gray-400 mt-1">
            Make sure the directory contains skills/, agents/, commands/, or AGENTS.md
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
              Import {selectedCount} Resource{selectedCount !== 1 ? 's' : ''} from Local System
            </button>
          </div>

          {/* CLI Command */}
          {importMutation.isSuccess && (
            <div className="bg-gray-900 text-gray-100 rounded-xl p-4">
              <div className="flex items-center justify-between mb-2">
                <div className="flex items-center gap-2">
                  <Terminal className="h-4 w-4 text-green-400" />
                  <span className="text-sm font-medium text-green-400">
                    Import complete! CLI equivalent:
                  </span>
                </div>
                <button
                  onClick={() => copyToClipboard(cliCommand)}
                  className="p-1.5 hover:bg-gray-700 rounded transition-colors"
                >
                  {copied ? (
                    <CheckIcon className="h-4 w-4 text-green-400" />
                  ) : (
                    <Copy className="h-4 w-4 text-gray-400" />
                  )}
                </button>
              </div>
              <code className="text-xs block">{cliCommand}</code>
            </div>
          )}

          {/* Import Error */}
          {importMutation.isError && (
            <div className="p-3 bg-red-50 border border-red-200 rounded-lg text-sm text-red-700">
              Import failed: {importMutation.error.message}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
