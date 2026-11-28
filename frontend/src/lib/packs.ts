import type { CollectionType } from '../types';

/** Where a pack comes from, for badges and filtering. */
export type PackSource = 'starter' | 'community' | 'mine';

/** The minimum a pack must expose to be classified. */
export interface PackSourceInput {
  is_starter_pack: boolean;
  owner_id: string;
}

export function packSource(collection: PackSourceInput, userId?: string): PackSource {
  if (collection.is_starter_pack) return 'starter';
  if (userId && collection.owner_id === userId) return 'mine';
  return 'community';
}

export function packSourceLabel(source: PackSource): string {
  if (source === 'starter') return 'Starter';
  if (source === 'mine') return 'Mine';
  return 'Community';
}

export function packKindLabel(collectionType: CollectionType): string {
  return collectionType === 'base' ? 'Starting point' : 'Add-on';
}

/**
 * Every pack opens the unified `/packs/:id` detail (ADR-0014 / Phase 5).
 * The old `/packs/community/:id` path is a redirect, not a second surface,
 * so `source` is retained for call-site compatibility but no longer changes
 * the destination.
 */
export function packHref(collection: { id: string }, _source?: PackSource): string {
  return `/packs/${collection.id}`;
}

/** The 12 adapters MyACE compiles to, in the order the storefront lists them. */
export const FRAMEWORK_LABELS: string[] = [
  'Claude Code',
  'Codex CLI',
  'Cursor',
  'OpenCode',
  'Copilot CLI',
  'Cline',
  'Windsurf',
  'Aider',
  'Continue',
  'Goose',
  'Amazon Q',
  'pi.dev',
];

/**
 * Adapter name/alias → display label. `target_compatibility` is hand-entered
 * metadata (AGENTS.md rule 41), so it can carry any adapter alias; map what
 * the 12 adapters actually declare and leave unknown values untouched.
 */
const FRAMEWORK_LABEL_BY_TARGET: Record<string, string> = {
  'claude-code': 'Claude Code',
  claude: 'Claude Code',
  'codex-cli': 'Codex CLI',
  codex: 'Codex CLI',
  cursor: 'Cursor',
  opencode: 'OpenCode',
  'copilot-cli': 'Copilot CLI',
  copilot: 'Copilot CLI',
  cline: 'Cline',
  windsurf: 'Windsurf',
  aider: 'Aider',
  continue: 'Continue',
  'continue-dev': 'Continue',
  goose: 'Goose',
  'amazon-q': 'Amazon Q',
  amazonq: 'Amazon Q',
  'pi-dev': 'pi.dev',
  pi: 'pi.dev',
};

export function frameworkLabel(target: string): string {
  return FRAMEWORK_LABEL_BY_TARGET[target] ?? target;
}

/**
 * "Works with" labels for a pack, derived from its items' descriptive
 * `target_compatibility`. That field is metadata and does not gate
 * compilation (AGENTS.md rule 41) — an empty union means no item narrowed
 * itself, i.e. every framework.
 */
export function packFrameworks(
  artifacts: { target_compatibility: string[] }[],
): string[] {
  const found = new Set<string>();
  for (const artifact of artifacts) {
    for (const target of artifact.target_compatibility) {
      found.add(FRAMEWORK_LABEL_BY_TARGET[target] ?? target);
    }
  }
  if (found.size === 0) return FRAMEWORK_LABELS;
  const order = (label: string) => {
    const index = FRAMEWORK_LABELS.indexOf(label);
    return index === -1 ? FRAMEWORK_LABELS.length : index;
  };
  return [...found].sort((a, b) => order(a) - order(b) || a.localeCompare(b));
}

/** "Updated 28 Nov 2026" from an ISO timestamp, or null when there is none. */
export function formatUpdated(iso: string | null | undefined): string | null {
  if (!iso) return null;
  const time = Date.parse(iso);
  if (Number.isNaN(time)) return null;
  const date = new Date(time).toLocaleDateString('en-GB', {
    day: 'numeric',
    month: 'short',
    year: 'numeric',
  });
  return `Updated ${date}`;
}

/**
 * The `layers_on` packs a setup does not contain yet. Advisory: callers show a
 * notice and never block (rule 42 — the user decides).
 */
export function missingLayers(
  setup: { base_collection_id: string | null; additional_collection_ids: string[] },
  layersOn: { id: string; name: string }[],
): { id: string; name: string }[] {
  return layersOn.filter(
    (ref) =>
      setup.base_collection_id !== ref.id && !setup.additional_collection_ids.includes(ref.id),
  );
}

export function formatUses(downloadCount: number): string {
  if (downloadCount >= 1000) {
    const thousands = downloadCount / 1000;
    return `${thousands >= 10 ? Math.round(thousands) : thousands.toFixed(1).replace(/\.0$/, '')}k uses`;
  }
  return `${downloadCount} ${downloadCount === 1 ? 'use' : 'uses'}`;
}


// ---------------------------------------------------------------------------
// Library filters (docs/plans/pack-discovery.md)
// ---------------------------------------------------------------------------

export type LibraryFacet = 'all' | 'base' | 'additional' | 'mine' | 'community';
export type LibrarySort = 'recommended' | 'rated' | 'recent';

export interface LibraryState {
  search: string;
  facet: LibraryFacet;
  category: string | null;
  topic: string | null;
  sort: LibrarySort;
}

const FACET_VALUES: LibraryFacet[] = ['all', 'base', 'additional', 'mine', 'community'];
const SORT_VALUES: LibrarySort[] = ['recommended', 'rated', 'recent'];

/** Read the library's filters from the URL, tolerating anything a user typed there. */
export function parseLibraryState(params: URLSearchParams): LibraryState {
  const facet = params.get('facet') as LibraryFacet | null;
  const sort = params.get('sort') as LibrarySort | null;
  return {
    search: params.get('q') ?? '',
    facet: facet && FACET_VALUES.includes(facet) ? facet : 'all',
    category: params.get('category') || null,
    topic: params.get('topic') || null,
    sort: sort && SORT_VALUES.includes(sort) ? sort : 'recommended',
  };
}

/** Serialize filters for the URL, omitting defaults so the default view is `/packs`. */
export function serializeLibraryState(state: LibraryState): URLSearchParams {
  const params = new URLSearchParams();
  if (state.search.trim()) params.set('q', state.search);
  if (state.facet !== 'all') params.set('facet', state.facet);
  if (state.category) params.set('category', state.category);
  if (state.topic) params.set('topic', state.topic);
  if (state.sort !== 'recommended') params.set('sort', state.sort);
  return params;
}

/** Name, description, category and topics, case-insensitively. */
export function packMatchesQuery(
  pack: { name: string; description?: string; category?: string },
  topics: string[],
  query: string,
): boolean {
  const needle = query.trim().toLowerCase();
  if (!needle) return true;
  return `${pack.name} ${pack.description ?? ''} ${pack.category ?? ''} ${topics.join(' ')}`
    .toLowerCase()
    .includes(needle);
}

/**
 * Topics worth offering as filter chips: those shared by at least `minPacks`
 * packs, most common first. A topic on a single pack is just that pack's name.
 */
export function topicFacets(
  packIds: string[],
  topicsById: Record<string, string[]>,
  { minPacks = 2, max = 14 }: { minPacks?: number; max?: number } = {},
): { topic: string; count: number }[] {
  const counts = new Map<string, number>();
  for (const id of packIds) {
    for (const topic of topicsById[id] ?? []) counts.set(topic, (counts.get(topic) ?? 0) + 1);
  }
  return [...counts.entries()]
    .filter(([, count]) => count >= minPacks)
    .map(([topic, count]) => ({ topic, count }))
    .sort((a, b) => b.count - a.count || a.topic.localeCompare(b.topic))
    .slice(0, max);
}
