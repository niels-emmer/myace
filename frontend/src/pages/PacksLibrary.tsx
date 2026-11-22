import { useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { FolderGit2, Plus, Search, Sparkles, Star, Upload } from 'lucide-react';
import { collectionsApi } from '../lib/api';
import { packApi } from '../lib/packApi';
import { BUNDLES } from '../lib/bundles';
import {
  formatUses,
  packHref,
  packKindLabel,
  packSource,
  packSourceLabel,
  type PackSource,
} from '../lib/packs';
import { useAuth } from '../contexts/AuthContext';
import type { Pack } from '../types/packs';

type Facet = 'all' | 'base' | 'additional' | 'mine' | 'community';
type Sort = 'recommended' | 'rated' | 'recent';

const FACETS: { id: Facet; label: string }[] = [
  { id: 'all', label: 'All' },
  { id: 'base', label: 'Starting points' },
  { id: 'additional', label: 'Add-ons' },
  { id: 'mine', label: 'Mine' },
  { id: 'community', label: 'Community' },
];

const SOURCE_CLASSES: Record<PackSource, string> = {
  starter: 'bg-brand-50 text-brand-700 border-brand-200',
  mine: 'bg-muted text-foreground border-border',
  community: 'bg-card text-muted-foreground border-border',
};

function createdAt(pack: Pack): number {
  return Date.parse(pack.updated_at || pack.created_at) || 0;
}

/**
 * Sort deliberately excludes "most used": `download_count` is advisory and
 * user-incrementable (invariant 25 / ADR-0015), so it is shown as a soft
 * "used N times" signal but never treated as an authoritative ranking.
 */
function sortPacks(packs: Pack[], sort: Sort): Pack[] {
  const copy = [...packs];
  if (sort === 'rated') {
    return copy.sort((a, b) => b.avg_rating - a.avg_rating || b.rating_count - a.rating_count);
  }
  if (sort === 'recent') {
    return copy.sort((a, b) => createdAt(b) - createdAt(a) || a.name.localeCompare(b.name));
  }
  // Recommended: starter packs first, starting points before add-ons, then rating.
  return copy.sort((a, b) => {
    if (a.is_starter_pack !== b.is_starter_pack) return a.is_starter_pack ? -1 : 1;
    if (a.collection_type !== b.collection_type) return a.collection_type === 'base' ? -1 : 1;
    return b.avg_rating - a.avg_rating || a.name.localeCompare(b.name);
  });
}

function emptyMessage(facet: Facet, anonymous: boolean): string {
  if (facet === 'mine') return 'You do not have any packs yet.';
  if (facet === 'community') {
    return anonymous
      ? 'No community packs match these filters yet.'
      : 'No community packs match these filters.';
  }
  if (facet === 'base') return 'No starting-point packs match these filters.';
  if (facet === 'additional') return 'No add-ons match these filters.';
  return anonymous ? 'No packs match these filters yet.' : 'No packs match these filters.';
}

export default function PacksLibrary() {
  const { user, isLoading: authLoading } = useAuth();
  const anonymous = !authLoading && !user;
  const [search, setSearch] = useState('');
  const [facet, setFacet] = useState<Facet>('all');
  const [category, setCategory] = useState<string | null>(null);
  const [sort, setSort] = useState<Sort>('recommended');

  const { data: collections, isLoading } = useQuery({
    queryKey: anonymous ? ['public-packs'] : ['collections'],
    queryFn: async () => {
      if (anonymous) {
        const response = await packApi.listCommunity({ limit: 100, sort: 'alpha' });
        return response.items;
      }
      return collectionsApi.list();
    },
    enabled: !authLoading,
  });

  const { data: categories } = useQuery({
    queryKey: anonymous ? ['public-pack-categories'] : ['community-categories'],
    queryFn: () =>
      anonymous ? packApi.communityCategories() : collectionsApi.listCommunityCategories(),
    enabled: !authLoading,
  });

  const packs = useMemo(() => {
    const query = search.trim().toLowerCase();
    const filtered = (collections ?? []).filter((collection) => {
      const source = packSource(collection, user?.id);
      if (anonymous && source !== 'community' && source !== 'starter') return false;
      if (facet === 'mine' && (anonymous || source !== 'mine')) return false;
      if (facet === 'community' && source !== 'community') return false;
      if (facet === 'base' && collection.collection_type !== 'base') return false;
      if (facet === 'additional' && collection.collection_type !== 'additional') return false;
      if (category && collection.category !== category) return false;
      if (!query) return true;
      return `${collection.name} ${collection.description ?? ''} ${collection.category ?? ''}`
        .toLowerCase()
        .includes(query);
    });
    return sortPacks(filtered, sort);
  }, [collections, facet, category, search, sort, user?.id, anonymous]);

  const bundlePacks = BUNDLES.map((bundle) => ({
    bundle,
    pack: (collections ?? []).find(
      (collection) =>
        collection.collection_type === 'base' &&
        collection.is_starter_pack &&
        collection.name === bundle.basePackName,
    ),
  }));

  const facets = anonymous ? FACETS.filter((item) => item.id !== 'mine') : FACETS;

  return (
    <div className="space-y-6">
      <div className="flex flex-col justify-between gap-4 sm:flex-row sm:items-start">
        <div>
          <h1 className="text-2xl font-bold text-foreground">Packs</h1>
          <p className="mt-1 text-muted-foreground">
            Rules, skills, agents, and workflows — curated starting points and community add-ons.
          </p>
        </div>
        {anonymous ? (
          <Link
            to="/login?mode=register"
            className="inline-flex items-center gap-2 rounded-lg bg-brand-600 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-brand-700"
          >
            Sign up free
          </Link>
        ) : (
          <div className="flex flex-wrap items-center gap-2">
            <Link
              to="/packs/import"
              className="inline-flex items-center gap-2 rounded-lg border border-border bg-card px-4 py-2 text-sm font-medium transition-colors hover:border-brand-600 hover:text-brand-600"
            >
              <Upload className="h-4 w-4" />
              Import packs
            </Link>
            <Link
              to="/packs/mine"
              className="inline-flex items-center gap-2 rounded-lg bg-brand-600 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-brand-700"
            >
              <Plus className="h-4 w-4" />
              New pack
            </Link>
          </div>
        )}
      </div>

      <div className="space-y-3 rounded-xl border border-border bg-card p-4">
        <div className="flex flex-col gap-3 lg:flex-row lg:items-center">
          <div className="relative min-w-0 flex-1">
            <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
            <input
              type="search"
              value={search}
              onChange={(event) => setSearch(event.target.value)}
              aria-label="Search packs"
              placeholder="Search packs, tags, categories…"
              className="w-full rounded-lg border border-input bg-background py-2 pl-9 pr-3 text-sm text-foreground focus:border-brand-500 focus:outline-none focus:ring-2 focus:ring-brand-500"
            />
          </div>
          <div className="flex flex-wrap items-center gap-2">
            {facets.map((item) => (
              <button
                key={item.id}
                onClick={() => setFacet(item.id)}
                aria-pressed={facet === item.id}
                className={`rounded-full border px-3 py-1.5 text-sm font-medium transition-colors ${
                  facet === item.id
                    ? 'border-brand-600 bg-brand-50 text-brand-700'
                    : 'border-border text-muted-foreground hover:bg-accent hover:text-accent-foreground'
                }`}
              >
                {item.label}
              </button>
            ))}
          </div>
          <select
            value={sort}
            onChange={(event) => setSort(event.target.value as Sort)}
            aria-label="Sort packs"
            className="rounded-lg border border-input bg-background px-3 py-2 text-sm text-foreground lg:ml-auto"
          >
            <option value="recommended">Recommended</option>
            <option value="rated">Highest rated</option>
            <option value="recent">Recently updated</option>
          </select>
        </div>

        {(categories ?? []).length > 0 && (
          <div className="flex flex-wrap items-center gap-2 border-t border-border pt-3">
            <span className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
              Category
            </span>
            <button
              onClick={() => setCategory(null)}
              aria-pressed={category === null}
              className={`rounded-full px-2.5 py-1 text-xs transition-colors ${
                category === null
                  ? 'bg-foreground text-background'
                  : 'bg-muted text-muted-foreground hover:text-foreground'
              }`}
            >
              All categories
            </button>
            {(categories ?? []).map((name) => (
              <button
                key={name}
                onClick={() => setCategory(name === category ? null : name)}
                aria-pressed={category === name}
                className={`rounded-full px-2.5 py-1 text-xs transition-colors ${
                  category === name
                    ? 'bg-foreground text-background'
                    : 'bg-muted text-muted-foreground hover:text-foreground'
                }`}
              >
                {name}
              </button>
            ))}
          </div>
        )}
      </div>

      {/* Featured "Start here" strip */}
      <div data-testid="start-here" className="rounded-xl border border-border bg-card p-4">
        <div className="flex items-center gap-3">
          <Sparkles className="h-5 w-5 shrink-0 text-brand-600" />
          <div>
            <p className="text-sm font-semibold text-card-foreground">Start here</p>
            <p className="text-sm text-muted-foreground">
              Four starter packs cover most people. Compose one into a setup.
            </p>
          </div>
        </div>
        <div className="mt-3 grid grid-cols-1 gap-2 sm:grid-cols-2 xl:grid-cols-4">
          {bundlePacks.map(({ bundle, pack }) => (
            <Link
              key={bundle.id}
              to={pack ? `/packs/${pack.id}` : '/packs'}
              className="rounded-lg border border-border px-3 py-2 transition-colors hover:border-brand-300 hover:bg-brand-50/50"
            >
              <p className="text-sm font-medium text-card-foreground">{bundle.name}</p>
              <p className="line-clamp-1 text-xs text-muted-foreground">
                {pack ? packKindLabel(pack.collection_type) : bundle.description}
              </p>
            </Link>
          ))}
        </div>
      </div>

      {isLoading ? (
        <p className="py-12 text-center text-sm text-muted-foreground">Loading packs…</p>
      ) : packs.length > 0 ? (
        <div data-testid="packs-grid" className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
          {packs.map((collection) => {
            const source = packSource(collection, user?.id);
            return (
              <Link
                key={collection.id}
                to={packHref(collection, source)}
                className="flex flex-col rounded-xl border border-border bg-card p-5 transition-shadow hover:border-input hover:shadow-xs"
              >
                <div className="flex items-center justify-between gap-2">
                  <span className="rounded bg-muted px-2 py-0.5 text-xs font-medium text-muted-foreground">
                    {packKindLabel(collection.collection_type)}
                  </span>
                  <span
                    className={`rounded border px-2 py-0.5 text-xs font-medium ${SOURCE_CLASSES[source]}`}
                  >
                    {packSourceLabel(source)}
                  </span>
                </div>
                <h2 className="mt-3 font-semibold text-card-foreground">{collection.name}</h2>
                <p className="mt-1 line-clamp-2 text-sm text-muted-foreground">
                  {collection.description || 'No description'}
                </p>
                <div className="mt-auto flex flex-wrap items-center gap-3 pt-4 text-xs text-muted-foreground">
                  {collection.rating_count > 0 && (
                    <span className="flex items-center gap-1">
                      <Star className="h-3 w-3" />
                      {collection.avg_rating.toFixed(1)}
                    </span>
                  )}
                  <span>{formatUses(collection.download_count)}</span>
                  <span>·</span>
                  <span>{collection.artifact_count} items</span>
                  {collection.category && <span>· {collection.category}</span>}
                </div>
              </Link>
            );
          })}
        </div>
      ) : (
        <div className="rounded-xl border border-border bg-card py-12 text-center">
          <FolderGit2 className="mx-auto mb-3 h-10 w-10 text-muted-foreground" />
          <p className="text-muted-foreground">{emptyMessage(facet, anonymous)}</p>
          <div className="mt-4 flex flex-wrap items-center justify-center gap-3">
            {anonymous ? (
              <Link
                to="/login?mode=register"
                className="inline-flex items-center gap-2 rounded-lg bg-brand-600 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-brand-700"
              >
                Sign up to create a pack
              </Link>
            ) : (
              <>
                <Link
                  to="/packs/mine"
                  className="inline-flex items-center gap-2 rounded-lg border border-border bg-card px-4 py-2 text-sm font-medium transition-colors hover:border-brand-600 hover:text-brand-600"
                >
                  <Plus className="h-4 w-4" />
                  Create a pack
                </Link>
                <Link
                  to="/packs/import"
                  className="inline-flex items-center gap-2 rounded-lg border border-border bg-card px-4 py-2 text-sm font-medium transition-colors hover:border-brand-600 hover:text-brand-600"
                >
                  <Upload className="h-4 w-4" />
                  Import packs
                </Link>
              </>
            )}
          </div>
        </div>
      )}

      <p className="text-sm text-muted-foreground">
        Showing {packs.length} of {collections?.length ?? 0} packs. Starter = bundled with MyACE ·
        Community = published by a user. Browsing is public; installing needs an account.
      </p>
    </div>
  );
}
