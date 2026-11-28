import { EFFECT_LABELS, capabilityLabel, parsePolicyRules } from '../lib/permissions';

/**
 * A pack's global permission rules as a readable list instead of raw JSON.
 * Restrict-only: a rule can ask first or block, never grant (ADR-0019).
 */
export function PolicyRules({ body }: { body: string }) {
  const rules = parsePolicyRules(body);
  return (
    <div className="space-y-2">
      <p className="text-xs text-muted-foreground">
        These rules only ever restrict — they ask first or block, and never grant access. They
        apply where the tool supports them: Claude Code and OpenCode (merged into your config
        with <code>myace pull --apply-permissions</code>) and, for shell commands, Codex CLI.
        Other tools get a compile warning and the written rules.
      </p>
      {rules.length > 0 ? (
        <table className="w-full text-left text-sm">
          <thead>
            <tr className="text-xs text-muted-foreground">
              <th className="pb-1 pr-4 font-medium">What</th>
              <th className="pb-1 pr-4 font-medium">Command</th>
              <th className="pb-1 font-medium">Rule</th>
            </tr>
          </thead>
          <tbody>
            {rules.map((rule) => (
              <tr key={`${rule.capability}|${rule.match}|${rule.effect}`} className="border-t border-border">
                <td className="py-1.5 pr-4 text-card-foreground">{capabilityLabel(rule.capability)}</td>
                <td className="py-1.5 pr-4 font-mono text-xs text-foreground">
                  {rule.match || 'any'}
                </td>
                <td className="py-1.5">
                  <span
                    className={`rounded px-1.5 py-0.5 text-xs font-medium ${
                      rule.effect === 'deny'
                        ? 'bg-red-50 text-red-700'
                        : 'bg-orange-50 text-orange-700'
                    }`}
                  >
                    {EFFECT_LABELS[rule.effect]}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      ) : (
        <p className="text-sm text-muted-foreground">No valid rules in this item.</p>
      )}
    </div>
  );
}
