/**
 * Public storefront API client.
 *
 * Kept separate from `lib/api.ts` (owned by another phase) so the anonymous
 * surface is explicit: every `get*` here hits a route that works without a
 * session (ADR-0014); the write helpers require one.
 */

import type { Artifact } from '../types';
import type {
  CommunityCollectionsResponse,
  Pack,
  PackMetadataUpdate,
} from '../types/packs';

const API_BASE = '/api/v1';

async function request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(options.headers as Record<string, string>),
  };

  const response = await fetch(`${API_BASE}${endpoint}`, {
    ...options,
    headers,
    credentials: 'same-origin',
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: response.statusText }));
    throw new Error(error.detail || `HTTP ${response.status}`);
  }

  if (response.status === 204) return undefined as T;
  return response.json();
}

/** The `?format=json` body of the anonymous pack-install route. */
export interface PackPreview {
  subject: string;
  pack_id: string;
  target: string;
  artifact_count: number;
  files: Record<string, string>;
  warnings: { level: string; code: string; message: string }[];
  compiled_hash: string;
}

/** A preview failure the UI can explain: 413 too large, 429 rate limited, 400 disabled target. */
export class PreviewError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.name = 'PreviewError';
    this.status = status;
  }
}

export const packApi = {
  /** Anonymous: published, approved packs. */
  listCommunity: (params?: {
    type?: string;
    category?: string;
    sort?: 'rating' | 'downloads' | 'alpha';
    offset?: number;
    limit?: number;
  }) => {
    const searchParams = new URLSearchParams();
    if (params?.type) searchParams.set('type', params.type);
    if (params?.category) searchParams.set('category', params.category);
    if (params?.sort) searchParams.set('sort', params.sort);
    if (params?.offset !== undefined) searchParams.set('offset', String(params.offset));
    if (params?.limit !== undefined) searchParams.set('limit', String(params.limit));
    const qs = searchParams.toString();
    return request<CommunityCollectionsResponse>(
      `/collections/community${qs ? `?${qs}` : ''}`,
    );
  },

  /**
   * Anonymous: every published pack, fetched page by page. The route caps one
   * page at 100, so a single call would silently truncate a bigger library.
   */
  listAllCommunity: async (params?: {
    type?: string;
    category?: string;
    sort?: 'rating' | 'downloads' | 'alpha';
  }) => {
    const pageSize = 100;
    const maxPages = 20;
    const items: Pack[] = [];
    for (let page = 0; page < maxPages; page += 1) {
      const response = await packApi.listCommunity({
        ...params,
        offset: page * pageSize,
        limit: pageSize,
      });
      items.push(...response.items);
      if (items.length >= response.total || response.items.length === 0) break;
    }
    return items;
  },

  /** Anonymous: topics per published pack (pack id to topics), derived from item tags. */
  communityTopics: () => request<Record<string, string[]>>('/collections/community/topics'),

  /** Anonymous: distinct categories among published packs. */
  communityCategories: () =>
    request<string[]>('/collections/community/categories'),

  /** Anonymous: one approved, published pack (404 otherwise). */
  getPublicPack: (id: string) =>
    request<Pack>(`/collections/community/${id}`),

  /** Anonymous: compile targets currently offered (adapter names). */
  getFrameworks: () => request<string[]>('/frameworks'),

  /**
   * Anonymous: what a published pack compiles to for one framework. Read-only,
   * never counts as a use (`install.md` does not touch `download_count`).
   */
  previewInstall: async (id: string, target: string): Promise<PackPreview> => {
    const response = await fetch(
      `${API_BASE}/collections/community/${id}/install.md?target=${encodeURIComponent(target)}&format=json`,
      { credentials: 'same-origin', headers: { Accept: 'application/json' } },
    );
    if (response.ok) return (await response.json()) as PackPreview;
    if (response.status === 413) {
      throw new PreviewError(413, 'This pack is too large to preview here. Download the zip instead.');
    }
    if (response.status === 429) {
      throw new PreviewError(429, 'Too many requests right now. Try again in a minute.');
    }
    const detail = await response.json().catch(() => ({ detail: response.statusText }));
    throw new PreviewError(response.status, detail.detail || `HTTP ${response.status}`);
  },

  /** Anonymous: the enabled contents of a published pack. */
  getPublicArtifacts: (id: string) =>
    request<Artifact[]>(`/collections/community/${id}/artifacts`),

  /**
   * Authenticated: write pack metadata before submitting for review. Kept
   * here (not in `lib/api.ts`) because `license` is not in the shared
   * `CollectionUpdate` type yet.
   */
  updateMetadata: (id: string, data: PackMetadataUpdate) =>
    request<Pack>(`/collections/${id}`, {
      method: 'PATCH',
      body: JSON.stringify(data),
    }),
};
