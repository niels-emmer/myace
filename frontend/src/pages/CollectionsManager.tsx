import { Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import {
  FolderGit2,
  Plus,
  GitBranch,
  Globe,
  Lock,
  ChevronRight,
  BookOpen,
  Grid3X3,
  Download,
} from 'lucide-react';
import { collectionsApi } from '../lib/api';
import type { Collection } from '../types';

export default function CollectionsManager() {
  const { data: collections, isLoading } = useQuery({
    queryKey: ['collections'],
    queryFn: () => collectionsApi.list(),
  });

  const { data: topCommunity, isLoading: loadingTop } = useQuery({
    queryKey: ['community-collections', 'top'],
    queryFn: () => collectionsApi.listCommunityTop(10),
  });

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex items-start justify-between gap-4">
        <div className="flex-1 min-w-0">
          <h1 className="text-2xl font-bold text-foreground">Collections</h1>
          <p className="text-muted-foreground mt-1">
            Groups of artifacts (rules, skills, agents, workflows) imported from GitHub or your local machine. Combine collections into a Profile to compile them for a target framework.
          </p>
        </div>
        <Link
          to="/import"
          className="flex-shrink-0 flex items-center gap-2 px-4 py-2 bg-brand-600 text-white rounded-lg hover:bg-brand-700 transition-colors text-sm font-medium"
        >
          <Plus className="h-4 w-4" />
          Import Collection
        </Link>
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
            <p className="text-muted-foreground">No collections yet. Import your first one!</p>
          </div>
        )}
      </div>

      {/* Community Collections */}
      <div>
        <div className="flex items-center justify-between mb-3">
          <h2 className="text-lg font-semibold text-foreground flex items-center gap-2">
            <BookOpen className="h-5 w-5 text-muted-foreground" />
            Community Collections
          </h2>
          <Link
            to="/collections/community"
            className="flex items-center gap-1.5 text-sm text-brand-600 hover:text-brand-700 font-medium transition-colors"
          >
            <Grid3X3 className="h-4 w-4" />
            Browse by category
            <ChevronRight className="h-4 w-4" />
          </Link>
        </div>
        <p className="text-sm text-muted-foreground mb-4">
          Discover collections published by the MyACE community. Import them into your workspace with one click.
        </p>

        {loadingTop ? (
          <div className="text-center py-8 text-muted-foreground">Loading community collections...</div>
        ) : topCommunity && topCommunity.length > 0 ? (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {topCommunity.map((collection) => (
              <CommunityCollectionCard key={collection.id} collection={collection} />
            ))}
          </div>
        ) : (
          <div className="text-center py-8 bg-card rounded-xl border border-border">
            <BookOpen className="h-12 w-12 text-muted-foreground mx-auto mb-3" />
            <p className="text-muted-foreground">No community collections yet. Be the first to publish!</p>
          </div>
        )}
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
          <p className="text-sm text-muted-foreground mt-0.5 truncate">
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

function CommunityCollectionCard({ collection }: { collection: Collection }) {
  return (
    <Link
      to={`/collections/community/${collection.id}`}
      className="block bg-card rounded-xl border border-border p-5 hover:shadow-sm transition-shadow group"
    >
      <div className="flex items-start justify-between mb-3">
        <div className="flex-1 min-w-0">
          <h3 className="font-semibold text-card-foreground group-hover:text-brand-600 transition-colors">
            {collection.name}
          </h3>
          <p className="text-sm text-muted-foreground mt-0.5 truncate">
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
        {collection.category && (
          <span className="px-1.5 py-0.5 rounded bg-muted text-muted-foreground font-medium">
            {collection.category}
          </span>
        )}
        <span className="flex items-center gap-1">
          <Download className="h-3 w-3" />
          {collection.download_count} downloads
        </span>
        <span>{collection.artifact_count} artifacts</span>
      </div>
    </Link>
  );
}
