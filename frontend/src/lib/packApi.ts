/**
 * Public storefront API client.
 *
 * Kept separate from `lib/api.ts` (owned by another phase) so the anonymous
 * surface is explicit: every `get*` here hits a route that works without a
 * session (ADR-0014), and `usePack` is the one authenticated call.
 */

import type { Artifact } from '../types';
import type {
  CommunityCollectionsResponse,
  Pack,
  PackMetadataUpdate,
  UsePackResult,
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

  /** Anonymous: distinct categories among published packs. */
  communityCategories: () =>
    request<string[]>('/collections/community/categories'),

  /** Anonymous: one approved, published pack (404 otherwise). */
  getPublicPack: (id: string) =>
    request<Pack>(`/collections/community/${id}`),

  /** Anonymous: the enabled contents of a published pack. */
  getPublicArtifacts: (id: string) =>
    request<Artifact[]>(`/collections/community/${id}/artifacts`),

  /**
   * Authenticated: record a reference use of a pack ("used N times").
   * Reference semantics — this never copies the pack (ADR-0015).
   */
  usePack: (id: string) =>
    request<UsePackResult>(`/collections/${id}/use`, { method: 'POST' }),

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
