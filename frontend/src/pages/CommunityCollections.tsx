import { useState } from 'react';
import { Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import {
  ArrowLeft,
  BookOpen,
  Download,
  ChevronRight,
  ChevronLeft,
  ChevronsLeft,
  ChevronsRight,
} from 'lucide-react';
import { collectionsApi } from '../lib/api';
import type { Collection } from '../types';

const PAGE_SIZE = 10;

type SortOption = 'downloads' | 'rating' | 'alpha';

const SORT_LABELS: Record<SortOption, string> = {
  downloads: 'Most downloaded',
  rating: 'Highest rated',
  alpha: 'Name (A–Z)',
};

export default function CommunityCollections() {
  const [collectionType, setCollectionType] = useState<string | null>(null);
  const [sort, setSort] = useState<SortOption>('downloads');
  const [page, setPage] = useState(0);

  const offset = page * PAGE_SIZE;

  const { data, isLoading } = useQuery({
    queryKey: ['community-collections', { type: collectionType, sort, page }],
    queryFn: () =>
      collectionsApi.listCommunity({
        ...(collectionType ? { type: collectionType } : {}),
        sort,
        offset,
        limit: PAGE_SIZE,
      }),
  });

  const collections = data?.items ?? [];
  const total = data?.total ?? 0;
  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE));

  const handleTypeChange = (type: string | null) => {
    setCollectionType(type);
    setPage(0);
  };

  const handleSortChange = (value: SortOption) => {
    setSort(value);
    setPage(0);
  };

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

      {/* Collection type filter + sort */}
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="flex flex-wrap items-center gap-2">
        <button
          onClick={() => handleTypeChange(null)}
          className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg border text-sm font-medium transition-colors ${
            collectionType === null
              ? 'border-brand-500 bg-brand-50 text-brand-700'
              : 'border-border text-muted-foreground hover:border-input hover:text-accent-foreground'
          }`}
        >
          All
        </button>
        <button
          onClick={() => handleTypeChange('base')}
          className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg border text-sm font-medium transition-colors ${
            collectionType === 'base'
              ? 'border-brand-500 bg-brand-50 text-brand-700'
              : 'border-border text-muted-foreground hover:border-input hover:text-accent-foreground'
          }`}
        >
          Base
        </button>
        <button
          onClick={() => handleTypeChange('additional')}
          className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg border text-sm font-medium transition-colors ${
            collectionType === 'additional'
              ? 'border-brand-500 bg-brand-50 text-brand-700'
              : 'border-border text-muted-foreground hover:border-input hover:text-accent-foreground'
          }`}
        >
          Additional
        </button>
        </div>

        <select
          value={sort}
          onChange={(e) => handleSortChange(e.target.value as SortOption)}
          className="px-3 py-1.5 bg-background text-foreground border border-input rounded-lg text-sm focus:ring-2 focus:ring-brand-500 focus:border-brand-500"
        >
          {(Object.keys(SORT_LABELS) as SortOption[]).map((key) => (
            <option key={key} value={key}>
              {SORT_LABELS[key]}
            </option>
          ))}
        </select>
      </div>

      {/* Collection list */}
      {isLoading ? (
        <div className="text-center py-12 text-muted-foreground">Loading collections...</div>
      ) : collections.length > 0 ? (
        <>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {collections.map((collection) => (
              <CommunityCollectionCard key={collection.id} collection={collection} />
            ))}
          </div>

          {/* Pagination */}
          {totalPages > 1 && (
            <div className="flex items-center justify-center gap-2 pt-2">
              <button
                onClick={() => setPage(0)}
                disabled={page === 0}
                className="p-2 rounded-lg border border-border text-muted-foreground hover:text-accent-foreground hover:bg-accent transition-colors disabled:opacity-30 disabled:pointer-events-none"
                title="First page"
              >
                <ChevronsLeft className="h-4 w-4" />
              </button>
              <button
                onClick={() => setPage(Math.max(0, page - 1))}
                disabled={page === 0}
                className="p-2 rounded-lg border border-border text-muted-foreground hover:text-accent-foreground hover:bg-accent transition-colors disabled:opacity-30 disabled:pointer-events-none"
                title="Previous page"
              >
                <ChevronLeft className="h-4 w-4" />
              </button>
              <span className="text-sm text-muted-foreground px-3">
                Page {page + 1} of {totalPages}
              </span>
              <button
                onClick={() => setPage(Math.min(totalPages - 1, page + 1))}
                disabled={page >= totalPages - 1}
                className="p-2 rounded-lg border border-border text-muted-foreground hover:text-accent-foreground hover:bg-accent transition-colors disabled:opacity-30 disabled:pointer-events-none"
                title="Next page"
              >
                <ChevronRight className="h-4 w-4" />
              </button>
              <button
                onClick={() => setPage(totalPages - 1)}
                disabled={page >= totalPages - 1}
                className="p-2 rounded-lg border border-border text-muted-foreground hover:text-accent-foreground hover:bg-accent transition-colors disabled:opacity-30 disabled:pointer-events-none"
                title="Last page"
              >
                <ChevronsRight className="h-4 w-4" />
              </button>
            </div>
          )}
        </>
      ) : (
        <div className="text-center py-12 bg-card rounded-xl border border-border">
          <BookOpen className="h-12 w-12 text-muted-foreground mx-auto mb-3" />
          <p className="text-muted-foreground">
            {collectionType
              ? `No ${collectionType} collections available yet.`
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
