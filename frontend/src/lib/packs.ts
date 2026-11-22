import type { Collection } from '../types';

/** Where a pack comes from, for badges and filtering. */
export type PackSource = 'starter' | 'community' | 'mine';

export function packSource(collection: Collection, userId?: string): PackSource {
  if (collection.is_starter_pack) return 'starter';
  if (userId && collection.owner_id === userId) return 'mine';
  return 'community';
}

export function packSourceLabel(source: PackSource): string {
  if (source === 'starter') return 'Starter';
  if (source === 'mine') return 'Mine';
  return 'Community';
}

export function packKindLabel(collectionType: Collection['collection_type']): string {
  return collectionType === 'base' ? 'Starting point' : 'Add-on';
}

/** Starter and own packs open the owner/editor view; community packs open the read-only community view. */
export function packHref(collection: Collection, source: PackSource): string {
  return source === 'community' ? `/packs/community/${collection.id}` : `/packs/${collection.id}`;
}

export function formatUses(downloadCount: number): string {
  if (downloadCount >= 1000) {
    const thousands = downloadCount / 1000;
    return `${thousands >= 10 ? Math.round(thousands) : thousands.toFixed(1).replace(/\.0$/, '')}k uses`;
  }
  return `${downloadCount} ${downloadCount === 1 ? 'use' : 'uses'}`;
}
