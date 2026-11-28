import type { Artifact } from '../types';

/**
 * Helpers for the permission model (ADR-0019). A pack's global rules are stored
 * as a `model_config` named `permissions:*`; an agent's own restrictions are its
 * `permissions` map. Both are restrict-only: nothing here ever grants access.
 */

export type PermissionEffect = 'ask' | 'deny';

export interface PolicyRule {
  capability: string;
  effect: PermissionEffect;
  match: string;
}

const CAPABILITY_LABELS: Record<string, string> = {
  read: 'Read files',
  edit: 'Edit files',
  execute: 'Run commands',
  network: 'Use the network',
  delegate: 'Start sub-agents',
};

export const EFFECT_LABELS: Record<PermissionEffect, string> = {
  ask: 'Ask first',
  deny: 'Blocked',
};

export function isPermissionPolicy(artifact: Pick<Artifact, 'artifact_type' | 'name'>): boolean {
  return artifact.artifact_type === 'model_config' && artifact.name.startsWith('permissions:');
}

export function capabilityLabel(capability: string): string {
  return CAPABILITY_LABELS[capability] ?? capability;
}

/** Parse a policy body; anything malformed yields no rules rather than throwing. */
export function parsePolicyRules(body: string): PolicyRule[] {
  try {
    const raw: unknown = JSON.parse(body);
    const rules = (raw as { rules?: unknown }).rules;
    if (!Array.isArray(rules)) return [];
    return rules.flatMap((item): PolicyRule[] => {
      const rule = item as Partial<PolicyRule>;
      if (
        typeof rule.capability !== 'string' ||
        (rule.effect !== 'ask' && rule.effect !== 'deny')
      ) {
        return [];
      }
      return [
        { capability: rule.capability, effect: rule.effect, match: rule.match ?? '' },
      ];
    });
  } catch {
    return [];
  }
}

/** An agent's restrictions as short phrases ("Cannot edit files"); `allow` is ignored. */
export function agentRestrictions(permissions: Artifact['permissions']): string[] {
  return Object.entries(permissions ?? {}).flatMap(([capability, effect]) => {
    const label = capabilityLabel(capability).toLowerCase();
    if (effect === 'deny') return [`Cannot ${label}`];
    if (effect === 'ask') return [`Asks before it can ${label}`];
    return [];
  });
}

/**
 * Files a pack ships to carry its global permission rules (ADR-0019). The
 * Claude Code and OpenCode sidecars are inert until merged; the Codex rules file
 * is live. Returns a short status for the install preview, or null for any other
 * file.
 */
export function permissionFileStatus(
  filename: string,
): { label: string; detail: string } | null {
  if (filename.endsWith('/myace.permissions.json')) {
    return {
      label: 'permission rules — not active yet',
      detail:
        'Your tool ignores this file until it is merged into its config. ' +
        'Run `myace pull --apply-permissions` (it shows a diff first) or merge it by hand.',
    };
  }
  if (filename === '.codex/rules/myace.rules') {
    return {
      label: 'permission rules — active in Codex',
      detail:
        'Codex loads this file by itself, next to your own rules. It can only ask first or block, never allow.',
    };
  }
  return null;
}
