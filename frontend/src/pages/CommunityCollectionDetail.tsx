import { useMemo, useState } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  ArrowLeft,
  BookOpen,
  Download,
  ChevronDown,
  ChevronRight,
  FileText,
  FolderGit2,
  Check,
  Loader2,
  ExternalLink,
  Pencil,
} from 'lucide-react';
import { collectionsApi, moderationApi } from '../lib/api';
import { useAuth } from '../contexts/AuthContext';
import type { Artifact, ArtifactType } from '../types';

const inputClass =
  'w-full px-3 py-2 bg-background text-foreground border border-input rounded-lg text-sm ' +
  'focus:ring-2 focus:ring-brand-500 focus:border-brand-500';

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

// Display order for artifact types: rules (from AGENTS.md), workflows,
// agents, skills, then anything else (e.g. model configs).
const TYPE_ORDER: ArtifactType[] = ['rule', 'workflow', 'agent', 'skill', 'model_config'];
const typeRank = (type: ArtifactType): number => {
  const idx = TYPE_ORDER.indexOf(type);
  return idx === -1 ? TYPE_ORDER.length : idx;
};

export default function CommunityCollectionDetail() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { user } = useAuth();
  const [typeFilter, setTypeFilter] = useState<ArtifactType | 'all'>('all');
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [importSuccess, setImportSuccess] = useState<string | null>(null);
  const [showMetaEditModal, setShowMetaEditModal] = useState(false);
  const [metaName, setMetaName] = useState('');
  const [metaDescription, setMetaDescription] = useState('');
  const [metaCategory, setMetaCategory] = useState('');

  const canEditMeta = user?.role === 'moderator' || user?.role === 'admin';

  const { data: collection, isLoading: loadingCollection } = useQuery({
    queryKey: ['community-collection', id],
    queryFn: () => collectionsApi.get(id!),
    enabled: !!id,
  });

  // Fetch the full artifact list once, unfiltered. Refetching per-type
  // (queryKey including typeFilter) would make the per-category counts below
  // — derived from this same list — see only the active category's artifacts
  // and show (0) for every other tab. Same bug, same fix as PR #51 on the
  // owned-collection page; keep both pages filtering client-side.
  const { data: artifacts, isLoading: loadingArtifacts } = useQuery({
    queryKey: ['community-artifacts', id],
    queryFn: () => collectionsApi.getArtifacts(id!, { include_disabled: true }),
    enabled: !!id,
  });

  const visibleArtifacts = useMemo(() => {
    const filtered =
      typeFilter === 'all'
        ? (artifacts ?? [])
        : (artifacts ?? []).filter((a) => a.artifact_type === typeFilter);
    return [...filtered].sort(
      (a, b) =>
        typeRank(a.artifact_type) - typeRank(b.artifact_type) ||
        a.name.localeCompare(b.name)
    );
  }, [artifacts, typeFilter]);

  const importMutation = useMutation({
    mutationFn: () => collectionsApi.importCommunity(id!),
    onSuccess: (result) => {
      setImportSuccess(result.collection_id);
      queryClient.invalidateQueries({ queryKey: ['collections'] });
      queryClient.invalidateQueries({ queryKey: ['community-collections'] });
    },
  });

  const updateMetaMutation = useMutation({
    mutationFn: () =>
      moderationApi.updateMeta(id!, {
        name: metaName.trim(),
        description: metaDescription.trim(),
        category: metaCategory.trim(),
      }),
    onSuccess: (updated) => {
      queryClient.setQueryData(['community-collection', id], updated);
      queryClient.invalidateQueries({ queryKey: ['community-collections'] });
      setShowMetaEditModal(false);
    },
  });

  const openMetaEditModal = () => {
    updateMetaMutation.reset();
    setMetaName(collection?.name ?? '');
    setMetaDescription(collection?.description ?? '');
    setMetaCategory(collection?.category ?? '');
    setShowMetaEditModal(true);
  };

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

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-start gap-4">
        <Link
          to="/collections/community"
          className="p-2 -ml-2 text-muted-foreground hover:text-accent-foreground hover:bg-accent rounded-lg transition-colors"
          title="Back to community collections"
        >
          <ArrowLeft className="h-5 w-5" />
        </Link>
        <div className="flex-1 min-w-0">
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
            {collection.category && (
              <span className="px-2 py-0.5 rounded text-xs font-medium bg-muted text-muted-foreground">
                {collection.category}
              </span>
            )}
          </div>
          <p className="text-muted-foreground mt-1">
            {collection.description || 'No description'}
          </p>
          <div className="flex items-center gap-4 text-xs text-muted-foreground mt-2">
            <span className="flex items-center gap-1">
              <Download className="h-3 w-3" />
              {collection.download_count} downloads
            </span>
            <span>{collection.artifact_count} artifacts</span>
            <span className="flex items-center gap-1">
              <BookOpen className="h-3 w-3" />
              Community collection
            </span>
          </div>
        </div>

        {/* Import + moderator actions */}
        <div className="flex-shrink-0 flex items-center gap-2">
          {canEditMeta && (
            <button
              onClick={openMetaEditModal}
              className="flex items-center gap-1.5 px-4 py-2 bg-muted border border-border rounded-lg text-sm text-foreground hover:bg-accent transition-colors"
            >
              <Pencil className="h-3.5 w-3.5" />
              Edit metadata
            </button>
          )}
          {importSuccess ? (
            <div className="flex items-center gap-2">
              <span className="text-sm text-green-600 font-medium flex items-center gap-1">
                <Check className="h-4 w-4" />
                Imported
              </span>
              <button
                onClick={() => navigate(`/collections/${importSuccess}`)}
                className="flex items-center gap-1.5 px-4 py-2 bg-brand-600 text-white rounded-lg hover:bg-brand-700 text-sm font-medium transition-colors"
              >
                <ExternalLink className="h-4 w-4" />
                View my copy
              </button>
            </div>
          ) : (
            <button
              onClick={() => importMutation.mutate()}
              disabled={importMutation.isPending}
              className="flex items-center gap-2 px-4 py-2 bg-brand-600 text-white rounded-lg hover:bg-brand-700 disabled:opacity-50 text-sm font-medium transition-colors"
            >
              {importMutation.isPending ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin" />
                  Importing...
                </>
              ) : (
                <>
                  <Download className="h-4 w-4" />
                  Import Collection
                </>
              )}
            </button>
          )}
        </div>
      </div>

      {/* Error state */}
      {importMutation.isError && (
        <div className="p-3 bg-destructive/10 border border-destructive/20 rounded-lg text-sm text-destructive">
          {(importMutation.error as Error).message}
        </div>
      )}

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
      </div>

      {/* Artifact List */}
      {loadingArtifacts ? (
        <div className="text-center py-12 text-muted-foreground">Loading artifacts...</div>
      ) : visibleArtifacts.length > 0 ? (
        <div className="bg-card rounded-xl border border-border divide-y divide-border">
          {visibleArtifacts.map((artifact) => (
            <ArtifactRow
              key={artifact.id}
              artifact={artifact}
              isExpanded={expandedId === artifact.id}
              onToggleExpand={() =>
                setExpandedId(expandedId === artifact.id ? null : artifact.id)
              }
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

      {/* Edit Metadata Modal (moderator/admin only) */}
      {showMetaEditModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-card border border-border rounded-xl p-6 w-full max-w-md space-y-4">
            <h2 className="text-lg font-semibold text-card-foreground flex items-center gap-2">
              <Pencil className="h-5 w-5" />
              Edit Metadata
            </h2>
            <p className="text-sm text-muted-foreground -mt-2">
              Moderator edit — only name, description, and category. Artifact content isn't
              affected.
            </p>
            <div>
              <label className="block text-sm font-medium text-foreground mb-1">Name</label>
              <input
                type="text"
                value={metaName}
                onChange={(e) => setMetaName(e.target.value)}
                className={inputClass}
                autoFocus
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-foreground mb-1">Description</label>
              <textarea
                value={metaDescription}
                onChange={(e) => setMetaDescription(e.target.value)}
                rows={3}
                className={inputClass}
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-foreground mb-1">Category</label>
              <input
                type="text"
                value={metaCategory}
                onChange={(e) => setMetaCategory(e.target.value)}
                className={inputClass}
              />
            </div>

            {updateMetaMutation.isError && (
              <p className="text-sm text-destructive">
                {(updateMetaMutation.error as Error).message}
              </p>
            )}

            <div className="flex justify-end gap-3">
              <button
                onClick={() => setShowMetaEditModal(false)}
                className="px-4 py-2 text-sm text-muted-foreground hover:text-accent-foreground"
              >
                Cancel
              </button>
              <button
                onClick={() => updateMetaMutation.mutate()}
                disabled={!metaName.trim() || updateMetaMutation.isPending}
                className="flex items-center gap-2 px-4 py-2 bg-brand-600 text-white rounded-lg hover:bg-brand-700 disabled:opacity-50 text-sm font-medium transition-colors"
              >
                {updateMetaMutation.isPending ? 'Saving...' : 'Save'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

function ArtifactRow({
  artifact,
  isExpanded,
  onToggleExpand,
}: {
  artifact: Artifact;
  isExpanded: boolean;
  onToggleExpand: () => void;
}) {
  return (
    <div>
      {/* Row header */}
      <div className="flex items-center gap-3 px-4 py-3 transition-colors">
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
        <div className="px-4 pb-4 pl-16">
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
