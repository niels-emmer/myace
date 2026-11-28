import { useState } from 'react';
import { ShieldCheck } from 'lucide-react';
import { capabilityLabel } from '../lib/permissions';
import type { Artifact } from '../types';

const CAPABILITIES = ['read', 'edit', 'execute', 'network', 'delegate'] as const;
type Choice = 'inherit' | 'ask' | 'deny';

const CHOICE_LABELS: Record<Choice, string> = {
  inherit: 'Inherit (no restriction)',
  ask: 'Ask first',
  deny: 'Block',
};

const choiceOf = (permissions: Artifact['permissions'], capability: string): Choice => {
  const value = permissions?.[capability];
  return value === 'ask' || value === 'deny' ? value : 'inherit';
};

/**
 * Edits one agent's per-capability restrictions (ADR-0019). Restrict-only on
 * purpose: there is no "allow" choice, and "Inherit" removes the key. Saves on
 * change; a failed save shows inline and the select snaps back to what is
 * stored, so a failure never leaves the UI claiming a restriction that isn't there.
 */
export default function AgentPermissionsEditor({
  permissions,
  onSave,
}: {
  permissions: Artifact['permissions'];
  onSave: (next: Record<string, 'ask' | 'deny'>) => Promise<unknown>;
}) {
  const [saving, setSaving] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const change = async (capability: string, choice: Choice) => {
    const next: Record<string, 'ask' | 'deny'> = {};
    for (const cap of CAPABILITIES) {
      const value = cap === capability ? choice : choiceOf(permissions, cap);
      if (value !== 'inherit') next[cap] = value;
    }
    setError(null);
    setSaving(capability);
    try {
      await onSave(next);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not save the permission change.');
    } finally {
      setSaving(null);
    }
  };

  return (
    <fieldset className="space-y-2 rounded-lg border border-border p-3">
      <legend className="flex items-center gap-1 px-1 text-xs font-medium text-muted-foreground">
        <ShieldCheck className="h-3.5 w-3.5 text-orange-600" />
        Permissions (can only restrict)
      </legend>
      <div className="grid gap-2 sm:grid-cols-2">
        {CAPABILITIES.map((capability) => (
          <label key={capability} className="flex items-center justify-between gap-3 text-sm">
            <span className="text-card-foreground">{capabilityLabel(capability)}</span>
            <select
              aria-label={capabilityLabel(capability)}
              value={choiceOf(permissions, capability)}
              disabled={saving !== null}
              onChange={(event) => change(capability, event.target.value as Choice)}
              className="rounded-lg border border-input bg-background px-2 py-1 text-xs text-foreground"
            >
              {(Object.keys(CHOICE_LABELS) as Choice[]).map((choice) => (
                <option key={choice} value={choice}>
                  {CHOICE_LABELS[choice]}
                </option>
              ))}
            </select>
          </label>
        ))}
      </div>
      {error && <p className="text-xs text-destructive">{error}</p>}
    </fieldset>
  );
}
