import { Link, useNavigate } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  FolderGit2,
  GitBranch,
  Globe,
  Lock,
  ChevronRight,
  BookOpen,
  HardDrive,
  Plus,
} from 'lucide-react';
import GithubIcon from '../components/GithubIcon';
import { collectionsApi } from '../lib/api';
import { packKindLabel } from '../lib/packs';
import { useAuth } from '../contexts/AuthContext';
import type { Collection } from '../types';

export default function CollectionsManager() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  const { data: collections, isLoading } = useQuery({
    queryKey: ['collections', { owner_id: user?.id }],
    queryFn: () => collectionsApi.list({ owner_id: user?.id }),
    enabled: !!user,
  });

  const createMutation = useMutation({
    mutationFn: () =>
      collectionsApi.create({
        name: 'Untitled pack',
        description: '',
        collection_type: 'base',
        git_url: 'manual://untitled',
      }),
    onSuccess: (created) => {
      queryClient.invalidateQueries({ queryKey: ['collections'] });
      navigate(`/packs/${created.id}`);
    },
  });

  return (
    <div className="space-y-8">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-foreground">My packs</h1>
        <p className="text-muted-foreground mt-1">
          A pack is a bundle of items — rules, skills, agents, and workflows — around a role or
          capability. Bring one in from{' '}
          <Link to="/packs/import?source=git" className="text-brand-600 hover:underline font-medium">
            any GitHub repository
          </Link>
          , from{' '}
          <Link to="/packs/import?source=local" className="text-brand-600 hover:underline font-medium">
            your local machine
          </Link>
          , or from the{' '}
          <Link to="/packs" className="text-brand-600 hover:underline font-medium">
            community library
          </Link>
          .
        </p>
        <p className="text-muted-foreground mt-2">
          Starting-point packs give you a complete baseline; add-on packs layer a specialty on top.
          Compose them into a setup, then install it into any framework you use.
        </p>
      </div>

      {/* My packs */}
      <div>
        <h2 className="text-lg font-semibold text-foreground mb-3 flex items-center gap-2">
          <FolderGit2 className="h-5 w-5 text-muted-foreground" />
          My packs
        </h2>
        {isLoading ? (
          <div className="text-center py-12 text-muted-foreground">Loading packs…</div>
        ) : collections && collections.length > 0 ? (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {collections.map((collection) => (
              <CollectionCard key={collection.id} collection={collection} />
            ))}
          </div>
        ) : (
          <div className="text-center py-12 bg-card rounded-xl border border-border">
            <FolderGit2 className="h-12 w-12 text-muted-foreground mx-auto mb-3" />
            <p className="text-muted-foreground mb-4">
              You don&rsquo;t have any packs yet. Get started by importing one:
            </p>
            <div className="flex flex-col sm:flex-row items-center justify-center gap-3">
              <Link
                to="/packs/import?source=local"
                className="flex items-center gap-2 px-4 py-2 bg-card border border-border rounded-lg hover:border-brand-600 hover:text-brand-600 transition-colors text-sm font-medium"
              >
                <HardDrive className="h-4 w-4" />
                Import from local machine
              </Link>
              <Link
                to="/packs/import?source=git"
                className="flex items-center gap-2 px-4 py-2 bg-card border border-border rounded-lg hover:border-brand-600 hover:text-brand-600 transition-colors text-sm font-medium"
              >
                <GithubIcon className="h-4 w-4" />
                Import from a GitHub repo
              </Link>
              <Link
                to="/packs"
                className="flex items-center gap-2 px-4 py-2 bg-card border border-border rounded-lg hover:border-brand-600 hover:text-brand-600 transition-colors text-sm font-medium"
              >
                <BookOpen className="h-4 w-4" />
                Browse community packs
              </Link>
            </div>
          </div>
        )}

        {/* Add a pack */}
        <div className="mt-4 flex flex-wrap items-center gap-3">
          <span className="text-sm font-medium text-foreground">Add a pack:</span>
          <button
            onClick={() => createMutation.mutate()}
            disabled={createMutation.isPending}
            className="flex items-center gap-2 px-4 py-2 bg-brand-600 text-white rounded-lg hover:bg-brand-700 disabled:opacity-50 transition-colors text-sm font-medium"
          >
            <Plus className="h-4 w-4" />
            {createMutation.isPending ? 'Creating…' : 'New pack'}
          </button>
          <Link
            to="/packs/import?source=git"
            className="flex items-center gap-2 px-4 py-2 bg-card border border-border rounded-lg hover:border-brand-600 hover:text-brand-600 transition-colors text-sm font-medium"
          >
            <GithubIcon className="h-4 w-4" />
            From GitHub
          </Link>
          <Link
            to="/packs"
            className="flex items-center gap-2 px-4 py-2 bg-card border border-border rounded-lg hover:border-brand-600 hover:text-brand-600 transition-colors text-sm font-medium"
          >
            <BookOpen className="h-4 w-4" />
            From the community
          </Link>
        </div>
      </div>
    </div>
  );
}

function CollectionCard({ collection }: { collection: Collection }) {
  return (
    <Link
      to={`/packs/${collection.id}`}
      className="block bg-card rounded-xl border border-border p-5 hover:shadow-xs transition-shadow group"
    >
      <div className="flex items-start justify-between mb-3">
        <div className="flex-1 min-w-0">
          <h3 className="font-semibold text-card-foreground group-hover:text-brand-600 transition-colors">
            {collection.name}
          </h3>
          <p className="text-sm text-muted-foreground mt-0.5 line-clamp-2">
            {collection.description || 'No description'}
          </p>
        </div>
        <div className="flex items-center gap-2 shrink-0 ml-3">
          <span className={`px-2 py-0.5 rounded text-xs font-medium ${
            collection.collection_type === 'base'
              ? 'bg-blue-50 text-blue-700'
              : 'bg-purple-50 text-purple-700'
          }`}>
            {packKindLabel(collection.collection_type)}
          </span>
          <ChevronRight className="h-4 w-4 text-muted-foreground/40 group-hover:text-brand-600 transition-colors" />
        </div>
      </div>
      <div className="flex items-center gap-4 text-xs text-muted-foreground">
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
        <span>{collection.artifact_count} items</span>
        {collection.published && (
          <span className="flex items-center gap-1 text-green-600">
            <BookOpen className="h-3 w-3" />
            published
          </span>
        )}
      </div>
    </Link>
  );
}
