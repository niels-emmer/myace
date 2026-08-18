// Shared validation for artifact fields editable both inline
// (CollectionDetail.tsx) and via the Add-rule form (NewArtifactRule.tsx) —
// keep these in sync in one place rather than duplicating the range/pattern
// in both call sites.

export const PRIORITY_MIN = 0;
export const PRIORITY_MAX = 100;
export const VERSION_PATTERN = /^\d+\.\d+\.\d+$/;

export function validatePriority(raw: string): { value: number } | { error: string } {
  const parsed = Number(raw);
  if (raw.trim() === '' || !Number.isInteger(parsed)) {
    return { error: 'Priority must be a whole number.' };
  }
  if (parsed < PRIORITY_MIN || parsed > PRIORITY_MAX) {
    return { error: `Priority must be between ${PRIORITY_MIN} and ${PRIORITY_MAX}.` };
  }
  return { value: parsed };
}

export function validateVersion(raw: string): { value: string } | { error: string } {
  const trimmed = raw.trim();
  if (!VERSION_PATTERN.test(trimmed)) {
    return { error: 'Version must look like 1.0.0 (MAJOR.MINOR.PATCH).' };
  }
  return { value: trimmed };
}
