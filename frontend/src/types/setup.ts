/**
 * Phase 2 setup/onboarding types.
 *
 * Kept out of `types/index.ts` on purpose: that file is shared with the Phase 5
 * storefront branch, and this module is the Phase 2 surface (onboarding draft,
 * install claims, companion apply, framework paths). Everything here mirrors
 * either the Phase 3 backend models (`ProfileInstall`, `User.onboarding_completed_at`)
 * or the companion server's `/health` and `/apply/*` responses — see
 * docs/onboarding-wizard.md.
 */

import type { Profile, ProfileCreate, SyncStatus } from './index';

export type InstallLocation = 'project' | 'machine';
export type InstallMethod = 'zip' | 'cli' | 'apply';

/** Mirrors backend `ProfileInstallRead` (`GET /profiles/{id}/installs`). */
export interface ProfileInstall {
  id: string;
  profile_id: string;
  target: string;
  location: InstallLocation;
  method: string;
  created_at: string;
  updated_at: string;
}

/** Body for `POST /profiles/{id}/installs`. A claim, never verification. */
export interface ProfileInstallCreate {
  target: string;
  location: InstallLocation;
  method: InstallMethod;
}

/**
 * `ProfileCreate` plus the Phase 3 multi-framework field. `types/index.ts`'s
 * `ProfileCreate` predates `target_frameworks`; `lib/setupApi.ts` posts this
 * shape directly rather than widening the shared type.
 */
export interface SetupProfileCreate extends ProfileCreate {
  target_frameworks?: string[];
}

/** Install state for one framework row on the setup page / Home card. */
export type InstallState = 'verified' | 'drift' | 'unverified' | 'not-installed';

export interface FrameworkRow {
  target: string;
  state: InstallState;
  /** From the install claim; null when nothing was claimed (e.g. CLI-only verification). */
  location: InstallLocation | null;
  /** SyncStatus.last_checked_at, when a sync report exists. */
  lastVerifiedAt: string | null;
  claim: ProfileInstall | null;
  sync: SyncStatus | null;
}

const STATE_PRECEDENCE: Record<InstallState, number> = {
  verified: 3,
  drift: 2,
  unverified: 1,
  'not-installed': 0,
};

/**
 * Status precedence: verified > drift > installed-not-verified > not installed.
 * `SyncStatus` is the only verified source (AGENTS.md rules 32/33); an install
 * claim only ever means "the user said they installed it", so it can never
 * outrank a sync report.
 */
export function installStateFor(
  sync: SyncStatus | undefined,
  claim: ProfileInstall | undefined,
): InstallState {
  if (sync) {
    if (sync.locally_modified_files.length > 0 || !sync.in_sync) return 'drift';
    return 'verified';
  }
  return claim ? 'unverified' : 'not-installed';
}

export function stateRank(state: InstallState): number {
  return STATE_PRECEDENCE[state];
}

/** The profile's frameworks, falling back to the deprecated single target. */
export function profileTargets(profile: Profile): string[] {
  if (profile.target_frameworks && profile.target_frameworks.length > 0) {
    return profile.target_frameworks;
  }
  return profile.target_framework ? [profile.target_framework] : [];
}

/**
 * Build the framework matrix. One row per configured target, plus any target
 * that only appears in sync reports or install claims (e.g. a framework
 * removed from the setup but still installed on disk) so status is never
 * silently dropped.
 */
export function buildFrameworkRows(
  profile: Profile,
  syncRows: SyncStatus[],
  claims: ProfileInstall[],
): FrameworkRow[] {
  const targets = new Set(profileTargets(profile));
  for (const row of syncRows) {
    if (row.profile_id === profile.id) targets.add(row.target);
  }
  for (const claim of claims) targets.add(claim.target);

  return [...targets].map((target) => {
    const sync = syncRows.find(
      (row) => row.profile_id === profile.id && row.target === target,
    );
    const claim = claims.find((row) => row.target === target) ?? null;
    return {
      target,
      state: installStateFor(sync, claim ?? undefined),
      location: claim?.location ?? null,
      lastVerifiedAt: sync?.last_checked_at ?? null,
      claim,
      sync: sync ?? null,
    };
  });
}

/**
 * Conventional install roots per framework, used to show "resolves to" before
 * anything is written. This is a hand-maintained mirror of the backend
 * adapters' `expected_paths()` and the companion's `MACHINE_SUBDIRS` — see
 * AGENTS.md rule 35 for the same syncing contract. A `null` machine path means
 * the framework's output is project-only and cannot be installed machine-wide.
 */
export interface FrameworkPaths {
  project: string;
  machine: string | null;
}

export const FRAMEWORK_PATHS: Record<string, FrameworkPaths> = {
  'claude-code': { project: './.claude', machine: '~/.claude' },
  opencode: { project: './.opencode', machine: '~/.config/opencode' },
  cursor: { project: './.cursor', machine: '~/.cursor' },
  'codex-cli': { project: './.codex', machine: '~/.codex' },
  'copilot-cli': { project: './.github', machine: null },
  cline: { project: './.clinerules', machine: null },
  windsurf: { project: './.windsurf', machine: '~/.windsurf' },
  aider: { project: './', machine: null },
  continue: { project: './.continue', machine: '~/.continue' },
  goose: { project: './', machine: null },
  'amazon-q': { project: './.amazonq', machine: '~/.amazonq' },
  'pi-dev': { project: './.pi', machine: '~/.pi' },
};

export function frameworkPaths(target: string): FrameworkPaths {
  return FRAMEWORK_PATHS[target] ?? { project: './', machine: null };
}

/** Human-readable resolved path for a framework + location choice. */
export function resolveInstallPath(target: string, location: InstallLocation): string {
  const paths = frameworkPaths(target);
  if (location === 'machine') return paths.machine ?? 'Not supported machine-wide';
  return paths.project;
}

export function supportsMachineInstall(target: string): boolean {
  return frameworkPaths(target).machine !== null;
}

// ─── Companion server (`myace serve`) ───────────────────────

export interface CompanionApplyCapability {
  supported: boolean;
  targets: string[];
  machine_targets: string[];
}

/** `GET /health` on the companion — only `apply` is relevant here. */
export interface CompanionHealth {
  status: string;
  server: string;
  apply?: CompanionApplyCapability;
  /**
   * Optional: a companion that knows which repository it is serving may
   * report it here, which lets the wizard default to project installs. The
   * shipped companion does not send it, so machine is the default.
   */
  project_root?: string;
  /** Candidate URL that actually answered; use it for follow-up calls. */
  baseUrl: string;
}

export interface CompanionApplyFile {
  relative_path: string;
  path: string;
  exists: boolean;
  bytes: number;
  sha256: string;
  old_sha256: string | null;
  action: 'added' | 'changed' | 'unchanged';
}

/** Response of `POST /apply/preview` (see cli/myace_cli/local_server.py). */
export interface CompanionApplyPreview {
  preview_id: string;
  profile_id: string;
  profile_name: string;
  target: string;
  location: InstallLocation;
  root: string;
  diff_hash: string;
  files: CompanionApplyFile[];
  warnings: { level: string; code: string; message: string }[];
}

/** Response of `POST /apply`. */
export interface CompanionApplyResult {
  profile_id: string;
  profile_name: string;
  target: string;
  location: InstallLocation;
  root: string;
  manifest: string | null;
  written: string[];
  backups: string[];
  unchanged: string[];
}

// ─── Onboarding draft ───────────────────────────────────────

export interface OnboardingDraft {
  step: number;
  frameworks: string[];
  /** Selected curated bundle, or null when the user picked packs directly. */
  bundleId: string | null;
  /** Base pack chosen (bundle base or an explicit starting point). */
  basePackId: string | null;
  addOnPackIds: string[];
  name: string;
  description: string;
  locations: Record<string, InstallLocation>;
  /** Created profile, reused when the user moves back and forth between steps. */
  profileId: string | null;
  /** Targets that already received an install claim in this draft. */
  claimedTargets: string[];
}
