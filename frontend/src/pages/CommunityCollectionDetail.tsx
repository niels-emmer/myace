import { useState } from 'react';
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
} from 'lucide-react';
import { collectionsApi } from '../lib/api';
import type { Artifact, ArtifactType } from '../types';

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

export default function CommunityCollectionDetail() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [typeFilter, setTypeFilter] = useState<ArtifactType | 'all'>('all');
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [importSuccess, setImportSuccess] = useState<string | null>(null);

  const { data: collection, isLoading: loadingCollection } = useQuery({
    queryKey: ['community-collection', id],
    queryFn: () => collectionsApi.get(id!),
    enabled: !!id,
  });

  const { data: artifacts, isLoading: loadingArtifacts } = useQuery({
    queryKey: ['community-artifacts', id, typeFilter],
    queryFn: () =>
      collectionsApi.getArtifacts(id!, {
        type: typeFilter === 'all' ? undefined : typeFilter,
        include_disabled: true,
      }),
    enabled: !!id,
  });

  const importMutation = useMutation({
    mutationFn: () => collectionsApi.importCommunity(id!),
    onSuccess: (result) => {
      setImportSuccess(result.collection_id);
      queryClient.invalidateQueries({ queryKey: ['collections'] });
      queryClient.invalidateQueries({ queryKey: ['community-collections'] });
    },
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

        {/* Import button */}
        <div className="flex-shrink-0">
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
      ) : artifacts && artifacts.length > 0 ? (
        <div className="bg-card rounded-xl border border-border divide-y divide-border">
          {artifacts.map((artifact) => (
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
