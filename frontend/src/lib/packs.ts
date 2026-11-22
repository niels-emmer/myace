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
    for (const target of artifact.target_compatibility) found.add(target);
  }
  return found.size > 0 ? [...found] : FRAMEWORK_LABELS;
}

export function formatUses(downloadCount: number): string {
  if (downloadCount >= 1000) {
    const thousands = downloadCount / 1000;
    return `${thousands >= 10 ? Math.round(thousands) : thousands.toFixed(1).replace(/\.0$/, '')}k uses`;
  }
  return `${downloadCount} ${downloadCount === 1 ? 'use' : 'uses'}`;
}
