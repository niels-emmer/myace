import { useState } from 'react';
import { Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import {
  ArrowLeft,
  BookOpen,
  Download,
  ChevronRight,
  Grid3X3,
} from 'lucide-react';
import { collectionsApi } from '../lib/api';
import type { Collection } from '../types';

export default function CommunityCollections() {
  const [selectedCategory, setSelectedCategory] = useState<string | null>(null);

  const { data: categories } = useQuery({
    queryKey: ['community-categories'],
    queryFn: () => collectionsApi.listCommunityCategories(),
  });

  const { data: collections, isLoading } = useQuery({
    queryKey: ['community-collections', selectedCategory],
    queryFn: () =>
      collectionsApi.listCommunity(
        selectedCategory ? { category: selectedCategory } : undefined,
      ),
  });

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-start gap-4">
        <Link
          to="/collections"
          className="p-2 -ml-2 text-muted-foreground hover:text-accent-foreground hover:bg-accent rounded-lg transition-colors"
          title="Back to collections"
        >
          <ArrowLeft className="h-5 w-5" />
        </Link>
        <div className="flex-1 min-w-0">
          <h1 className="text-2xl font-bold text-foreground flex items-center gap-2">
            <BookOpen className="h-6 w-6 text-muted-foreground" />
            Community Collections
          </h1>
          <p className="text-muted-foreground mt-1">
            Discover and import collections published by the MyACE community.
          </p>
        </div>
      </div>

      {/* Category filter */}
      {categories && categories.length > 0 && (
        <div className="flex flex-wrap items-center gap-2">
          <button
            onClick={() => setSelectedCategory(null)}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg border text-sm font-medium transition-colors ${
              selectedCategory === null
                ? 'border-brand-500 bg-brand-50 text-brand-700'
                : 'border-border text-muted-foreground hover:border-input hover:text-accent-foreground'
            }`}
          >
            <Grid3X3 className="h-4 w-4" />
            All
          </button>
          {categories.map((cat) => (
            <button
              key={cat}
              onClick={() => setSelectedCategory(cat)}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg border text-sm font-medium transition-colors ${
                selectedCategory === cat
                  ? 'border-brand-500 bg-brand-50 text-brand-700'
                  : 'border-border text-muted-foreground hover:border-input hover:text-accent-foreground'
              }`}
            >
              {cat}
            </button>
          ))}
        </div>
      )}

      {/* Collection list */}
      {isLoading ? (
        <div className="text-center py-12 text-muted-foreground">Loading collections...</div>
      ) : collections && collections.length > 0 ? (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {collections.map((collection) => (
            <CommunityCollectionCard key={collection.id} collection={collection} />
          ))}
        </div>
      ) : (
        <div className="text-center py-12 bg-card rounded-xl border border-border">
          <BookOpen className="h-12 w-12 text-muted-foreground mx-auto mb-3" />
          <p className="text-muted-foreground">
            {selectedCategory
              ? `No collections in the "${selectedCategory}" category yet.`
              : 'No community collections yet.'}
          </p>
        </div>
      )}
    </div>
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
