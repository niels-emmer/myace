/**
 * Types for the public storefront and the unified pack detail.
 *
 * The public read endpoints return the same `Collection`/`Artifact` shapes
 * the authenticated API does, so these aliases deliberately reuse the
 * existing types rather than forking them. `frontend/src/types/index.ts` is
 * owned by another phase; keep new pack-only shapes here.
 */

import type { CollectionType, ModerationStatus } from '../types';

/**
 * The sanitized pack shape the public storefront returns
 * (`PublicCollectionRead`, ADR-0014) — it intentionally omits `git_url`,
 * `visibility`, and the moderation-workflow fields. A full `Collection`
 * (authenticated reads) is structurally assignable to this, so signed-in
 * surfaces can use the same page types.
 *
 * `types/index.ts` is owned by another phase, so pack-only shapes live here.
 */
export interface Pack {
  id: string;
  owner_id: string;
  name: string;
  description?: string;
  collection_type: CollectionType;
  artifact_count: number;
  download_count: number;
  published: boolean;
  category?: string;
  license?: string | null;
  is_starter_pack: boolean;
  avg_rating: number;
  rating_count: number;
  moderation_status: ModerationStatus;
  /** Owner-only (authenticated reads); never returned by the public schema. */
  moderation_reason?: string | null;
  last_verified_at?: string | null;
  created_at: string;
  updated_at: string;
}

/** Paginated response from `GET /collections/community`. */
export interface CommunityCollectionsResponse {
  items: Pack[];
  total: number;
}

/** Fields the publish wizard writes before submitting for review. */
export interface PackMetadataUpdate {
  name?: string;
  description?: string;
  category?: string;
  license?: string | null;
}

export type PackTab = 'overview' | 'contents' | 'ratings';

/**
 * Moderation states surfaced by the publish wizard's status tracker.
 * `denied` is presented as "Changes requested" (rule 18's wording), and
 * `unpublished` is distinct from `draft` (ADR-0013).
 */
export type PublishStatus =
  | 'draft'
  | 'submitted'
  | 'approved'
  | 'denied'
  | 'unpublished';

/** Draft values held by the publish wizard between steps. */
export interface PublishDraft {
  name: string;
  description: string;
  category: string;
  license: string;
}
