/**
 * Phase 2 setup API — onboarding completion, install claims, and the local
 * companion's apply endpoints.
 *
 * Deliberately separate from `lib/api.ts`: that module is a declared Phase 5
 * hotspot, and splitting the fetches keeps the two branches' diffs disjoint.
 * It uses the same `{ detail }` error convention as `lib/api.ts` so pages can
 * show `error.message` for both.
 */

import type { Profile, ProfileCreate } from '../types';
import type {
  CompanionApplyPreview,
  CompanionApplyResult,
  CompanionHealth,
  InstallLocation,
  OnboardingDraft,
  ProfileInstall,
  ProfileInstallCreate,
  SetupProfileCreate,
} from '../types/setup';

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
    throw new Error(
      typeof error.detail === 'string' ? error.detail : `HTTP ${response.status}`,
    );
  }

  if (response.status === 204) return undefined as T;
  return response.json();
}

/** `POST /profiles` / `PUT /profiles/{id}` with `target_frameworks` included. */
export const setupProfilesApi = {
  create: (data: SetupProfileCreate) =>
    request<Profile>('/profiles', { method: 'POST', body: JSON.stringify(data) }),

  update: (id: string, data: SetupProfileCreate) =>
    request<Profile>(`/profiles/${id}`, { method: 'PUT', body: JSON.stringify(data) }),
};

/** `PATCH /auth/me/onboarding` — always the caller's own row. */
export const onboardingApi = {
  setCompleted: (completed: boolean) =>
    request<unknown>('/auth/me/onboarding', {
      method: 'PATCH',
      body: JSON.stringify({ completed }),
    }),
};

/** Install *claims* — never verification (docs/adr/0015-pack-reference-freeze.md). */
export const installsApi = {
  list: (profileId: string) =>
    request<ProfileInstall[]>(`/profiles/${profileId}/installs`),

  claim: (profileId: string, body: ProfileInstallCreate) =>
    request<ProfileInstall>(`/profiles/${profileId}/installs`, {
      method: 'POST',
      body: JSON.stringify(body),
    }),
};

// ─── Companion (`myace serve`) ──────────────────────────────

/**
 * The companion binds 127.0.0.1 only, so on a machine where `localhost`
 * resolves to ::1 the first candidate never answers. Follow-up calls must use
 * the `baseUrl` that answered `/health` — same rule as `useCompanionHealth`.
 */
export const COMPANION_URLS = ['http://localhost:8765', 'http://127.0.0.1:8765'];

export const COMPANION_HEADER = 'X-MyACE-Companion';

export async function fetchCompanionHealth(): Promise<CompanionHealth> {
  for (const baseUrl of COMPANION_URLS) {
    try {
      const res = await fetch(`${baseUrl}/health`, {
        mode: 'cors',
        cache: 'no-cache',
        signal: AbortSignal.timeout(3000),
      });
      if (res.ok) {
        return { ...(await res.json()), baseUrl } as CompanionHealth;
      }
    } catch {
      // Candidate didn't answer — try the next one. Do not log: this runs on
      // every poll for users who do not have the companion installed.
    }
  }
  throw new Error('Companion unreachable at localhost:8765 or 127.0.0.1:8765');
}

export interface CompanionAuditTarget {
  detected: boolean;
  artifact_count: number;
}

export interface CompanionAuditResult {
  path: string;
  score: number;
  targets: Record<string, CompanionAuditTarget>;
}

async function companionPost<T>(baseUrl: string, path: string, body: unknown): Promise<T> {
  const res = await fetch(`${baseUrl}${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', [COMPANION_HEADER]: '1' },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const error = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(error.detail || `Companion request failed (${res.status})`);
  }
  return res.json() as Promise<T>;
}

export const companionApi = {
  /** Detected frameworks under the companion's home directory, for step 1. */
  auditHome: (baseUrl: string) =>
    companionPost<CompanionAuditResult>(baseUrl, '/audit', { path: '~' }),

  previewApply: (
    baseUrl: string,
    body: { profile_id: string; target: string; location: InstallLocation },
  ) => companionPost<CompanionApplyPreview>(baseUrl, '/apply/preview', body),

  apply: (
    baseUrl: string,
    body: {
      profile_id: string;
      target: string;
      location: InstallLocation;
      preview_id: string;
      confirm: true;
    },
  ) => companionPost<CompanionApplyResult>(baseUrl, '/apply', body),
};

// ─── Onboarding draft persistence ───────────────────────────

const DRAFT_KEY = 'myace.onboarding.v1';

export const EMPTY_DRAFT: OnboardingDraft = {
  step: 1,
  frameworks: [],
  bundleId: null,
  basePackId: null,
  addOnPackIds: [],
  name: 'My setup',
  description: '',
  locations: {},
  profileId: null,
  claimedTargets: [],
};

export function loadDraft(): OnboardingDraft | null {
  try {
    const raw = window.localStorage.getItem(DRAFT_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw) as Partial<OnboardingDraft>;
    return { ...EMPTY_DRAFT, ...parsed };
  } catch {
    return null;
  }
}

export function saveDraft(draft: OnboardingDraft): void {
  try {
    window.localStorage.setItem(DRAFT_KEY, JSON.stringify(draft));
  } catch {
    // Storage can be unavailable (private mode, quota). The draft is a
    // convenience, never a requirement — the wizard still works in memory.
  }
}

export function clearDraft(): void {
  try {
    window.localStorage.removeItem(DRAFT_KEY);
  } catch {
    // See saveDraft.
  }
}

/**
 * Resolve the starting draft from the URL first, then localStorage. The URL
 * wins so a link like `/onboarding?step=3&pack=<id>` (returned by the import
 * branch) resumes at exactly that point even on a device with a stale draft.
 */
export function resolveInitialDraft(
  searchParams: URLSearchParams,
  stored: OnboardingDraft | null,
): OnboardingDraft {
  const draft: OnboardingDraft = { ...EMPTY_DRAFT, ...(stored ?? {}) };
  const stepParam = Number(searchParams.get('step'));
  if (Number.isInteger(stepParam) && stepParam >= 1 && stepParam <= 5) {
    draft.step = stepParam;
  }
  const packParam = searchParams.get('pack');
  if (packParam) {
    draft.basePackId = packParam;
    draft.bundleId = null;
  }
  return draft;
}

/** Profile payload derived from a draft. `target_frameworks` is the Phase 3 field. */
export function draftToProfileCreate(
  draft: OnboardingDraft,
  options: { baseCollectionId: string; additionalCollectionIds: string[] },
): SetupProfileCreate {
  return {
    name: draft.name.trim() || 'My setup',
    description: draft.description.trim() || undefined,
    base_collection_id: options.baseCollectionId,
    additional_collection_ids: options.additionalCollectionIds,
    disabled_artifact_ids: [],
    target_frameworks: draft.frameworks,
    is_public: false,
  } satisfies ProfileCreate & { target_frameworks: string[] };
}
