import { useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  ArrowLeft,
  GitBranch,
  Globe,
  Lock,
  ToggleLeft,
  ToggleRight,
  ChevronDown,
  ChevronRight,
  FileText,
  FolderGit2,
  Pencil,
  Check,
  X,
  AlertTriangle,
  FolderOutput,
  Trash2,
  Github,
  ExternalLink,
} from 'lucide-react';
import { collectionsApi } from '../lib/api';
import type { Artifact, ArtifactType, CollectionType } from '../types';

const ARTIFACT_TYPES: { value: ArtifactType | 'all'; label: string }[] = [
  { value: 'all', label: 'All' },
  { value: 'rule', label: 'Rules' },
  { value: 'skill', label: 'Skills' },
  { value: 'agent', label: 'Agents' },
  { value: 'workflow', label: 'Workflows' },
  { value: 'model_config', label: 'Model Configs' },
];

const typeColors: Record<string, string> = {
  rule: 'bg-blue-50 text-blue-700',
  skill: 'bg-green-50 text-green-700',
  agent: 'bg-purple-50 text-purple-700',
  workflow: 'bg-amber-50 text-amber-700',
  model_config: 'bg-rose-50 text-rose-700',
};

const inputClass =
  'w-full px-3 py-2 bg-background text-foreground border border-input rounded-lg text-sm focus:ring-2 focus:ring-brand-500 focus:border-brand-500';

export default function CollectionDetail() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [typeFilter, setTypeFilter] = useState<ArtifactType | 'all'>('all');
  const [expandedId, setExpandedId] = useState<string | null>(null);

  // Inline collection editing
  const [isEditing, setIsEditing] = useState(false);
  const [editForm, setEditForm] = useState({ name: '', description: '', collection_type: 'base' as CollectionType });

  // Row selection + bulk actions
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [showBulkMenu, setShowBulkMenu] = useState(false);
  const [showExportModal, setShowExportModal] = useState(false);
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
  const [exportMode, setExportMode] = useState<'existing' | 'new'>('existing');
  const [exportTargetId, setExportTargetId] = useState('');
  const [newCollName, setNewCollName] = useState('');
  const [newCollDesc, setNewCollDesc] = useState('');
  const [newCollType, setNewCollType] = useState<CollectionType>('base');

  // GitHub export
  const [showGithubModal, setShowGithubModal] = useState(false);
  const [ghRepo, setGhRepo] = useState('');
  const [ghBaseBranch, setGhBaseBranch] = useState('main');
  const [ghNewBranch, setGhNewBranch] = useState('');
  const [ghPrTitle, setGhPrTitle] = useState('');
  const [ghPrBody, setGhPrBody] = useState('');
  const [ghToken, setGhToken] = useState('');

  const { data: collection, isLoading: loadingCollection } = useQuery({
    queryKey: ['collection', id],
    queryFn: () => collectionsApi.get(id!),
    enabled: !!id,
  });

  const { data: artifacts, isLoading: loadingArtifacts } = useQuery({
    queryKey: ['artifacts', id, typeFilter],
    queryFn: () =>
      collectionsApi.getArtifacts(id!, {
        type: typeFilter === 'all' ? undefined : typeFilter,
        include_disabled: true,
      }),
    enabled: !!id,
  });

  const { data: allCollections } = useQuery({
    queryKey: ['collections'],
    queryFn: () => collectionsApi.list(),
    enabled: showExportModal,
  });

  const toggleMutation = useMutation({
    mutationFn: ({ artifactId, is_enabled }: { artifactId: string; is_enabled: boolean }) =>
      collectionsApi.updateArtifact(id!, artifactId, { is_enabled }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['artifacts', id] });
    },
  });

  const updateCollectionMutation = useMutation({
    mutationFn: () =>
      collectionsApi.update(id!, {
        name: editForm.name,
        description: editForm.description,
        collection_type: editForm.collection_type,
      }),
    onSuccess: (updated) => {
      queryClient.setQueryData(['collection', id], updated);
      queryClient.invalidateQueries({ queryKey: ['collections'] });
      setIsEditing(false);
    },
  });

  const bulkDeleteMutation = useMutation({
    mutationFn: (artifactIds: string[]) => collectionsApi.bulkDeleteArtifacts(id!, artifactIds),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['artifacts', id] });
      queryClient.invalidateQueries({ queryKey: ['collection', id] });
      setSelectedIds(new Set());
      setShowDeleteConfirm(false);
    },
  });

  const bulkExportMutation = useMutation({
    mutationFn: () =>
      collectionsApi.bulkExportArtifacts(id!, {
        artifact_ids: Array.from(selectedIds),
        ...(exportMode === 'existing'
          ? { target_collection_id: exportTargetId }
          : {
              new_collection_name: newCollName.trim(),
              new_collection_description: newCollDesc.trim(),
              new_collection_type: newCollType,
            }),
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['collections'] });
      setSelectedIds(new Set());
      setShowExportModal(false);
    },
  });

  const githubExportMutation = useMutation({
    mutationFn: () =>
      collectionsApi.exportToGithub(id!, {
        repo: ghRepo.trim(),
        base_branch: ghBaseBranch.trim() || 'main',
        new_branch: ghNewBranch.trim(),
        pr_title: ghPrTitle.trim(),
        pr_body: ghPrBody.trim(),
        github_token: ghToken,
      }),
  });

  if (loadingCollection) {
    return (
      <div className="text-center py-12 text-muted-foreground">Loading collection...</div>
    );
  }

  if (!collection) {
    return (
      <div className="text-center py-12 text-muted-foreground">Collection not found.</div>
    );
  }

  const typeCounts: Record<string, number> = {};
  if (artifacts) {
    artifacts.forEach((a) => {
      typeCounts[a.artifact_type] = (typeCounts[a.artifact_type] || 0) + 1;
    });
  }

  const startEdit = () => {
    setEditForm({
      name: collection.name,
      description: collection.description ?? '',
      collection_type: collection.collection_type,
    });
    setIsEditing(true);
  };

  const toggleSelect = (artifactId: string) => {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (next.has(artifactId)) next.delete(artifactId);
      else next.add(artifactId);
      return next;
    });
  };

  const selectAll = () => setSelectedIds(new Set((artifacts ?? []).map((a) => a.id)));
  const selectNone = () => setSelectedIds(new Set());

  const openExportModal = () => {
    setShowBulkMenu(false);
    setExportMode('existing');
    setExportTargetId('');
    setNewCollName('');
    setNewCollDesc('');
    setNewCollType('base');
    setShowExportModal(true);
  };

  const openDeleteConfirm = () => {
    setShowBulkMenu(false);
    setShowDeleteConfirm(true);
  };

  const canConfirmExport =
    exportMode === 'existing' ? !!exportTargetId : newCollName.trim().length > 0;

  const openGithubModal = () => {
    githubExportMutation.reset();
    setGhRepo('');
    setGhBaseBranch('main');
    setGhNewBranch('');
    setGhPrTitle(`Export "${collection.name}" from MyACE`);
    setGhPrBody('');
    setGhToken('');
    setShowGithubModal(true);
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-start gap-4">
        <button
          onClick={() => navigate('/collections')}
          className="p-2 -ml-2 text-muted-foreground hover:text-accent-foreground hover:bg-accent rounded-lg transition-colors"
          title="Back to collections"
        >
          <ArrowLeft className="h-5 w-5" />
        </button>
        <div className="flex-1 min-w-0">
          {isEditing ? (
            <div className="space-y-3 max-w-lg">
              <div>
                <label className="block text-xs font-medium text-muted-foreground mb-1">Name</label>
                <input
                  type="text"
                  value={editForm.name}
                  onChange={(e) => setEditForm({ ...editForm, name: e.target.value })}
                  className={`${inputClass} text-lg font-bold`}
                  autoFocus
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-muted-foreground mb-1">Description</label>
                <textarea
                  value={editForm.description}
                  onChange={(e) => setEditForm({ ...editForm, description: e.target.value })}
                  rows={2}
                  className={inputClass}
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-muted-foreground mb-1">Type</label>
                <select
                  value={editForm.collection_type}
                  onChange={(e) =>
                    setEditForm({ ...editForm, collection_type: e.target.value as CollectionType })
                  }
                  className={inputClass}
                >
                  <option value="base">Base Collection</option>
                  <option value="additional">Additional Collection</option>
                </select>
              </div>
            </div>
          ) : (
            <>
              <div className="flex items-center gap-3">
                <h1 className="text-2xl font-bold text-foreground truncate">{collection.name}</h1>
                <span
                  className={`px-2 py-0.5 rounded text-xs font-medium flex-shrink-0 ${
                    collection.collection_type === 'base'
                      ? 'bg-blue-50 text-blue-700'
                      : 'bg-purple-50 text-purple-700'
                  }`}
                >
                  {collection.collection_type}
                </span>
              </div>
              <p className="text-muted-foreground mt-1">
                {collection.description || 'No description'}
              </p>
              <div className="flex items-center gap-4 text-xs text-muted-foreground mt-2">
                <span className="flex items-center gap-1">
                  <GitBranch className="h-3 w-3" />
                  {collection.git_branch}
                </span>
                <span className="flex items-center gap-1">
                  {collection.visibility === 'public' ? (
                    <Globe className="h-3 w-3" />
                  ) : (
                    <Lock className="h-3 w-3" />
                  )}
                  {collection.visibility}
                </span>
                <span>{collection.artifact_count} artifacts</span>
              </div>
            </>
          )}
        </div>

        {/* Header actions */}
        <div className="flex items-center gap-2 flex-shrink-0">
          {!isEditing && selectedIds.size > 0 && (
            <div className="relative">
              <button
                onClick={() => setShowBulkMenu((v) => !v)}
                className="flex items-center gap-1.5 px-3 py-2 bg-muted border border-border rounded-lg text-sm text-foreground hover:bg-accent transition-colors"
              >
                With selected ({selectedIds.size})
                <ChevronDown className="h-3.5 w-3.5" />
              </button>
              {showBulkMenu && (
                <>
                  <div className="fixed inset-0 z-10" onClick={() => setShowBulkMenu(false)} />
                  <div className="absolute right-0 mt-1 w-56 bg-card border border-border rounded-lg shadow-lg z-20 py-1">
                    <button
                      onClick={openExportModal}
                      className="w-full flex items-center gap-2 px-3 py-2 text-sm text-foreground hover:bg-accent transition-colors text-left"
                    >
                      <FolderOutput className="h-4 w-4" />
                      Export to collection...
                    </button>
                    <button
                      onClick={openDeleteConfirm}
                      className="w-full flex items-center gap-2 px-3 py-2 text-sm text-destructive hover:bg-destructive/10 transition-colors text-left"
                    >
                      <Trash2 className="h-4 w-4" />
                      Delete selected
                    </button>
                  </div>
                </>
              )}
            </div>
          )}

          {isEditing ? (
            <>
              <button
                onClick={() => setIsEditing(false)}
                className="flex items-center gap-1.5 px-3 py-2 text-sm text-muted-foreground hover:text-accent-foreground transition-colors"
              >
                <X className="h-4 w-4" />
                Cancel
              </button>
              <button
                onClick={() => updateCollectionMutation.mutate()}
                disabled={!editForm.name.trim() || updateCollectionMutation.isPending}
                className="flex items-center gap-1.5 px-4 py-2 bg-brand-600 text-white rounded-lg hover:bg-brand-700 disabled:opacity-50 transition-colors text-sm font-medium"
              >
                <Check className="h-4 w-4" />
                {updateCollectionMutation.isPending ? 'Saving...' : 'Save'}
              </button>
            </>
          ) : (
            <>
              <button
                onClick={openGithubModal}
                title="Export this collection's enabled artifacts to a GitHub branch + PR"
                className="flex items-center gap-1.5 px-4 py-2 bg-muted border border-border rounded-lg text-sm text-foreground hover:bg-accent transition-colors"
              >
                <Github className="h-3.5 w-3.5" />
                Export to GitHub
              </button>
              <button
                onClick={startEdit}
                className="flex items-center gap-1.5 px-4 py-2 bg-muted border border-border rounded-lg text-sm text-foreground hover:bg-accent transition-colors"
              >
                <Pencil className="h-3.5 w-3.5" />
                Edit
              </button>
            </>
          )}
        </div>
      </div>

      {/* Type Filter Bar */}
      <div className="flex flex-wrap items-center gap-2">
        {ARTIFACT_TYPES.map((t) => {
          const count =
            t.value === 'all'
              ? artifacts?.length ?? 0
              : typeCounts[t.value] ?? 0;
          return (
            <button
              key={t.value}
              onClick={() => setTypeFilter(t.value)}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg border text-sm font-medium transition-colors ${
                typeFilter === t.value
                  ? 'border-brand-500 bg-brand-50 text-brand-700'
                  : 'border-border text-muted-foreground hover:border-input hover:text-accent-foreground'
              }`}
            >
              {t.label}
              <span className="text-xs opacity-60">({count})</span>
            </button>
          );
        })}

        {selectedIds.size > 0 && (
          <div className="flex items-center gap-3 text-sm ml-2 pl-2 border-l border-border">
            <span className="text-muted-foreground">{selectedIds.size} selected</span>
            <button onClick={selectAll} className="text-brand-600 hover:underline">
              Select all ({artifacts?.length ?? 0})
            </button>
            <button onClick={selectNone} className="text-brand-600 hover:underline">
              Select none
            </button>
          </div>
        )}
      </div>

      {/* Artifact List */}
      {loadingArtifacts ? (
        <div className="text-center py-12 text-muted-foreground">Loading artifacts...</div>
      ) : artifacts && artifacts.length > 0 ? (
        <div className="bg-card rounded-xl border border-border divide-y divide-border">
          {artifacts.map((artifact) => (
            <ArtifactRow
              key={artifact.id}
              artifact={artifact}
              isSelected={selectedIds.has(artifact.id)}
              onToggleSelect={() => toggleSelect(artifact.id)}
              isExpanded={expandedId === artifact.id}
              onToggleExpand={() =>
                setExpandedId(expandedId === artifact.id ? null : artifact.id)
              }
              onToggleEnabled={() =>
                toggleMutation.mutate({
                  artifactId: artifact.id,
                  is_enabled: !artifact.is_enabled,
                })
              }
              isToggling={toggleMutation.isPending}
            />
          ))}
        </div>
      ) : (
        <div className="text-center py-12 bg-card rounded-xl border border-border">
          <FolderGit2 className="h-12 w-12 text-muted-foreground mx-auto mb-3" />
          <p className="text-muted-foreground">
            {typeFilter === 'all'
              ? 'This collection has no artifacts.'
              : `No ${typeFilter} artifacts in this collection.`}
          </p>
        </div>
      )}

      {/* Export Modal */}
      {showExportModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-card border border-border rounded-xl p-6 w-full max-w-md space-y-4">
            <h2 className="text-lg font-semibold text-card-foreground">
              Export {selectedIds.size} item{selectedIds.size === 1 ? '' : 's'}
            </h2>

            <div className="flex gap-2">
              <button
                onClick={() => setExportMode('existing')}
                className={`flex-1 px-3 py-2 rounded-lg border text-sm font-medium transition-colors ${
                  exportMode === 'existing'
                    ? 'border-brand-500 bg-brand-50 text-brand-700'
                    : 'border-border text-muted-foreground hover:border-input'
                }`}
              >
                Existing collection
              </button>
              <button
                onClick={() => setExportMode('new')}
                className={`flex-1 px-3 py-2 rounded-lg border text-sm font-medium transition-colors ${
                  exportMode === 'new'
                    ? 'border-brand-500 bg-brand-50 text-brand-700'
                    : 'border-border text-muted-foreground hover:border-input'
                }`}
              >
                New collection
              </button>
            </div>

            {exportMode === 'existing' ? (
              <div>
                <label className="block text-sm font-medium text-foreground mb-1">Target collection</label>
                <select
                  value={exportTargetId}
                  onChange={(e) => setExportTargetId(e.target.value)}
                  className={inputClass}
                >
                  <option value="">Select a collection...</option>
                  {(allCollections ?? [])
                    .filter((c) => c.id !== id)
                    .map((c) => (
                      <option key={c.id} value={c.id}>
                        {c.name}
                      </option>
                    ))}
                </select>
              </div>
            ) : (
              <div className="space-y-3">
                <div>
                  <label className="block text-sm font-medium text-foreground mb-1">Name</label>
                  <input
                    type="text"
                    value={newCollName}
                    onChange={(e) => setNewCollName(e.target.value)}
                    className={inputClass}
                    autoFocus
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-foreground mb-1">Description</label>
                  <input
                    type="text"
                    value={newCollDesc}
                    onChange={(e) => setNewCollDesc(e.target.value)}
                    className={inputClass}
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-foreground mb-1">Type</label>
                  <select
                    value={newCollType}
                    onChange={(e) => setNewCollType(e.target.value as CollectionType)}
                    className={inputClass}
                  >
                    <option value="base">Base Collection</option>
                    <option value="additional">Additional Collection</option>
                  </select>
                </div>
              </div>
            )}

            {bulkExportMutation.isError && (
              <p className="text-sm text-destructive">
                {(bulkExportMutation.error as Error).message}
              </p>
            )}

            <div className="flex justify-end gap-3 pt-2">
              <button
                onClick={() => setShowExportModal(false)}
                className="px-4 py-2 text-sm text-muted-foreground hover:text-accent-foreground"
              >
                Cancel
              </button>
              <button
                onClick={() => bulkExportMutation.mutate()}
                disabled={!canConfirmExport || bulkExportMutation.isPending}
                className="px-4 py-2 bg-brand-600 text-white rounded-lg hover:bg-brand-700 disabled:opacity-50 text-sm font-medium transition-colors"
              >
                {bulkExportMutation.isPending ? 'Exporting...' : 'Export'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Delete Confirmation */}
      {showDeleteConfirm && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-card border border-border rounded-xl p-6 w-full max-w-sm space-y-4">
            <div className="flex items-start gap-3">
              <div className="p-2 bg-destructive/10 rounded-lg flex-shrink-0">
                <AlertTriangle className="h-5 w-5 text-destructive" />
              </div>
              <div>
                <h2 className="text-lg font-semibold text-card-foreground">
                  Delete {selectedIds.size} item{selectedIds.size === 1 ? '' : 's'}?
                </h2>
                <p className="text-sm text-muted-foreground mt-1">
                  This action cannot be undone. The selected artifacts will be permanently
                  removed from this collection.
                </p>
              </div>
            </div>

            {bulkDeleteMutation.isError && (
              <p className="text-sm text-destructive">
                {(bulkDeleteMutation.error as Error).message}
              </p>
            )}

            <div className="flex justify-end gap-3">
              <button
                onClick={() => setShowDeleteConfirm(false)}
                className="px-4 py-2 text-sm text-muted-foreground hover:text-accent-foreground"
              >
                Cancel
              </button>
              <button
                onClick={() => bulkDeleteMutation.mutate(Array.from(selectedIds))}
                disabled={bulkDeleteMutation.isPending}
                className="px-4 py-2 bg-destructive text-white rounded-lg hover:bg-destructive/90 disabled:opacity-50 text-sm font-medium transition-colors"
              >
                {bulkDeleteMutation.isPending ? 'Deleting...' : 'Delete'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* GitHub Export Modal */}
      {showGithubModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-card border border-border rounded-xl p-6 w-full max-w-md space-y-4 max-h-[90vh] overflow-y-auto">
            <h2 className="text-lg font-semibold text-card-foreground flex items-center gap-2">
              <Github className="h-5 w-5" />
              Export to GitHub
            </h2>
            <p className="text-sm text-muted-foreground -mt-2">
              Pushes this collection's enabled artifacts as canonical files on a new branch
              and opens a pull request. Model configs aren't round-trippable and are skipped.
            </p>

            {githubExportMutation.isSuccess ? (
              <div className="space-y-4">
                <div className="p-3 bg-green-50 border border-green-200 rounded-lg text-sm text-green-800">
                  Opened PR #{githubExportMutation.data.pr_number} with{' '}
                  {githubExportMutation.data.files_exported} file
                  {githubExportMutation.data.files_exported === 1 ? '' : 's'} on branch{' '}
                  <code className="bg-green-100 px-1 rounded">{githubExportMutation.data.branch}</code>
                  {githubExportMutation.data.skipped_model_configs > 0 && (
                    <> ({githubExportMutation.data.skipped_model_configs} model_config artifact
                    {githubExportMutation.data.skipped_model_configs === 1 ? '' : 's'} skipped)</>
                  )}
                  .
                </div>
                <a
                  href={githubExportMutation.data.pr_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex items-center justify-center gap-2 px-4 py-2 bg-brand-600 text-white rounded-lg hover:bg-brand-700 text-sm font-medium transition-colors"
                >
                  View Pull Request
                  <ExternalLink className="h-4 w-4" />
                </a>
                <div className="flex justify-end">
                  <button
                    onClick={() => setShowGithubModal(false)}
                    className="px-4 py-2 text-sm text-muted-foreground hover:text-accent-foreground"
                  >
                    Close
                  </button>
                </div>
              </div>
            ) : (
              <>
                <div>
                  <label className="block text-sm font-medium text-foreground mb-1">Repository</label>
                  <input
                    type="text"
                    value={ghRepo}
                    onChange={(e) => setGhRepo(e.target.value)}
                    placeholder="owner/repo or https://github.com/owner/repo"
                    className={`${inputClass} font-mono`}
                    autoFocus
                  />
                </div>
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="block text-sm font-medium text-foreground mb-1">Base branch</label>
                    <input
                      type="text"
                      value={ghBaseBranch}
                      onChange={(e) => setGhBaseBranch(e.target.value)}
                      placeholder="main"
                      className={`${inputClass} font-mono`}
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-foreground mb-1">
                      New branch <span className="text-muted-foreground font-normal">(optional)</span>
                    </label>
                    <input
                      type="text"
                      value={ghNewBranch}
                      onChange={(e) => setGhNewBranch(e.target.value)}
                      placeholder="auto-generated"
                      className={`${inputClass} font-mono`}
                    />
                  </div>
                </div>
                <div>
                  <label className="block text-sm font-medium text-foreground mb-1">PR title</label>
                  <input
                    type="text"
                    value={ghPrTitle}
                    onChange={(e) => setGhPrTitle(e.target.value)}
                    className={inputClass}
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-foreground mb-1">
                    PR description <span className="text-muted-foreground font-normal">(optional)</span>
                  </label>
                  <textarea
                    value={ghPrBody}
                    onChange={(e) => setGhPrBody(e.target.value)}
                    rows={2}
                    className={inputClass}
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-foreground mb-1">GitHub Token</label>
                  <input
                    type="password"
                    value={ghToken}
                    onChange={(e) => setGhToken(e.target.value)}
                    placeholder="ghp_..."
                    className={`${inputClass} font-mono`}
                  />
                  <p className="text-xs text-muted-foreground mt-1">
                    Needs `repo` scope. Used only for this request — never stored.
                  </p>
                </div>

                {githubExportMutation.isError && (
                  <p className="text-sm text-destructive">
                    {(githubExportMutation.error as Error).message}
                  </p>
                )}

                <div className="flex justify-end gap-3 pt-2">
                  <button
                    onClick={() => setShowGithubModal(false)}
                    className="px-4 py-2 text-sm text-muted-foreground hover:text-accent-foreground"
                  >
                    Cancel
                  </button>
                  <button
                    onClick={() => githubExportMutation.mutate()}
                    disabled={!ghRepo.trim() || !ghToken.trim() || githubExportMutation.isPending}
                    className="flex items-center gap-2 px-4 py-2 bg-brand-600 text-white rounded-lg hover:bg-brand-700 disabled:opacity-50 text-sm font-medium transition-colors"
                  >
                    {githubExportMutation.isPending ? 'Opening PR...' : 'Open Pull Request'}
                  </button>
                </div>
              </>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

function ArtifactRow({
  artifact,
  isSelected,
  onToggleSelect,
  isExpanded,
  onToggleExpand,
  onToggleEnabled,
  isToggling,
}: {
  artifact: Artifact;
  isSelected: boolean;
  onToggleSelect: () => void;
  isExpanded: boolean;
  onToggleExpand: () => void;
  onToggleEnabled: () => void;
  isToggling: boolean;
}) {
  return (
    <div>
      {/* Row header */}
      <div
        className={`flex items-center gap-3 px-4 py-3 transition-colors ${
          artifact.is_enabled ? '' : 'opacity-50'
        } ${isSelected ? 'bg-brand-50/50' : ''}`}
      >
        {/* Select checkbox */}
        <input
          type="checkbox"
          checked={isSelected}
          onChange={onToggleSelect}
          className="h-4 w-4 rounded border-input text-brand-600 focus:ring-brand-500 flex-shrink-0"
        />

        {/* Enable/disable toggle */}
        <button
          onClick={onToggleEnabled}
          disabled={isToggling}
          className={`p-1 rounded transition-colors ${
            artifact.is_enabled
              ? 'text-brand-600 hover:bg-brand-50'
              : 'text-muted-foreground hover:bg-muted'
          }`}
          title={artifact.is_enabled ? 'Disable' : 'Enable'}
        >
          {artifact.is_enabled ? (
            <ToggleRight className="h-5 w-5" />
          ) : (
            <ToggleLeft className="h-5 w-5" />
          )}
        </button>

        {/* Expand toggle */}
        <button
          onClick={onToggleExpand}
          className="p-1 text-muted-foreground hover:text-accent-foreground hover:bg-accent rounded transition-colors"
        >
          {isExpanded ? (
            <ChevronDown className="h-4 w-4" />
          ) : (
            <ChevronRight className="h-4 w-4" />
          )}
        </button>

        {/* Name */}
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <span className="text-sm font-medium text-card-foreground truncate">
              {artifact.name}
            </span>
            <span
              className={`px-1.5 py-0.5 rounded text-xs font-medium flex-shrink-0 ${
                typeColors[artifact.artifact_type] || 'bg-muted text-muted-foreground'
              }`}
            >
              {artifact.artifact_type}
            </span>
          </div>
        </div>

        {/* Priority */}
        <span className="text-xs text-muted-foreground flex-shrink-0">
          p{artifact.priority}
        </span>

        {/* Version */}
        <span className="text-xs text-muted-foreground flex-shrink-0">
          v{artifact.version}
        </span>
      </div>

      {/* Expanded body */}
      {isExpanded && (
        <div className="px-4 pb-4 pl-20">
          {artifact.description && (
            <p className="text-sm text-muted-foreground mb-3">{artifact.description}</p>
          )}
          <div className="bg-muted rounded-lg p-3 overflow-x-auto max-h-80 overflow-y-auto">
            <pre className="text-xs text-foreground whitespace-pre-wrap font-mono">
              {artifact.body}
            </pre>
          </div>
          <div className="flex items-center gap-4 mt-2 text-xs text-muted-foreground">
            <span className="flex items-center gap-1">
              <FileText className="h-3 w-3" />
              {artifact.file_path}
            </span>
            {artifact.tags.length > 0 && (
              <span>Tags: {artifact.tags.join(', ')}</span>
            )}
            {artifact.target_compatibility.length > 0 && (
              <span>Targets: {artifact.target_compatibility.join(', ')}</span>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
