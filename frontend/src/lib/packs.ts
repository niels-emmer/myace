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

export function formatUses(downloadCount: number): string {
  if (downloadCount >= 1000) {
    const thousands = downloadCount / 1000;
    return `${thousands >= 10 ? Math.round(thousands) : thousands.toFixed(1).replace(/\.0$/, '')}k uses`;
  }
  return `${downloadCount} ${downloadCount === 1 ? 'use' : 'uses'}`;
}
