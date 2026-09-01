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
        name: 'Untitled collection',
        description: '',
        collection_type: 'base',
        git_url: 'manual://untitled',
      }),
    onSuccess: (created) => {
      queryClient.invalidateQueries({ queryKey: ['collections'] });
      navigate(`/collections/${created.id}`);
    },
  });

  return (
    <div className="space-y-8">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-foreground">My Collections</h1>
        <p className="text-muted-foreground mt-1">
          Collections are groups of artifacts (rules, skills, agents, workflows) serving a
          role or specific function in agentic coding. They can be imported from{' '}
          <Link to="/machine/import?source=git" className="text-brand-600 hover:underline font-medium">
            any GitHub repository
          </Link>
          , from{' '}
          <Link to="/machine/import?source=local" className="text-brand-600 hover:underline font-medium">
            your local machine
          </Link>
          , or imported from the{' '}
          <Link to="/collections/community" className="text-brand-600 hover:underline font-medium">
            Community Collections
          </Link>
          .
        </p>
        <p className="text-muted-foreground mt-2">
          Base collections select your coding profile, additional collections add specific
          roles and skills. Combine them into a Profile for your project, and compile them to
          any framework.
        </p>
      </div>

      {/* My Collections */}
      <div>
        <h2 className="text-lg font-semibold text-foreground mb-3 flex items-center gap-2">
          <FolderGit2 className="h-5 w-5 text-muted-foreground" />
          My Collections
        </h2>
        {isLoading ? (
          <div className="text-center py-12 text-muted-foreground">Loading collections...</div>
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
              You don't have any collections yet. Get started by importing one:
            </p>
            <div className="flex flex-col sm:flex-row items-center justify-center gap-3">
              <Link
                to="/machine/import?source=local"
                className="flex items-center gap-2 px-4 py-2 bg-card border border-border rounded-lg hover:border-brand-600 hover:text-brand-600 transition-colors text-sm font-medium"
              >
                <HardDrive className="h-4 w-4" />
                Import from local machine
              </Link>
              <Link
                to="/machine/import?source=git"
                className="flex items-center gap-2 px-4 py-2 bg-card border border-border rounded-lg hover:border-brand-600 hover:text-brand-600 transition-colors text-sm font-medium"
              >
                <GithubIcon className="h-4 w-4" />
                Import from a GitHub repo
              </Link>
              <Link
                to="/collections/community"
                className="flex items-center gap-2 px-4 py-2 bg-card border border-border rounded-lg hover:border-brand-600 hover:text-brand-600 transition-colors text-sm font-medium"
              >
                <BookOpen className="h-4 w-4" />
                Browse community collections
              </Link>
            </div>
          </div>
        )}

        {/* Add a collection */}
        <div className="mt-4 flex flex-wrap items-center gap-3">
          <span className="text-sm font-medium text-foreground">Add a collection:</span>
          <button
            onClick={() => createMutation.mutate()}
            disabled={createMutation.isPending}
            className="flex items-center gap-2 px-4 py-2 bg-brand-600 text-white rounded-lg hover:bg-brand-700 disabled:opacity-50 transition-colors text-sm font-medium"
          >
            <Plus className="h-4 w-4" />
            {createMutation.isPending ? 'Creating...' : 'New'}
          </button>
          <Link
            to="/machine/import?source=git"
            className="flex items-center gap-2 px-4 py-2 bg-card border border-border rounded-lg hover:border-brand-600 hover:text-brand-600 transition-colors text-sm font-medium"
          >
            <GithubIcon className="h-4 w-4" />
            From GitHub
          </Link>
          <Link
            to="/collections/community"
            className="flex items-center gap-2 px-4 py-2 bg-card border border-border rounded-lg hover:border-brand-600 hover:text-brand-600 transition-colors text-sm font-medium"
          >
            <BookOpen className="h-4 w-4" />
            From the Community Collections
          </Link>
        </div>
      </div>
    </div>
  );
}

function CollectionCard({ collection }: { collection: Collection }) {
  return (
    <Link
      to={`/collections/${collection.id}`}
      className="block bg-card rounded-xl border border-border p-5 hover:shadow-sm transition-shadow group"
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
        <div className="flex items-center gap-2 flex-shrink-0 ml-3">
          <span className={`px-2 py-0.5 rounded text-xs font-medium ${
            collection.collection_type === 'base'
              ? 'bg-blue-50 text-blue-700'
              : 'bg-purple-50 text-purple-700'
          }`}>
            {collection.collection_type}
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
        <span>{collection.artifact_count} artifacts</span>
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
