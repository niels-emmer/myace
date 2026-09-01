import type { Artifact } from '../types';

/**
 * A name collision between two artifacts in *different* collections of a
 * composed profile — the client-side mirror of the backend's `name_collision`
 * compile-time warning (AGENTS.md rule 29/32). Surfaced in the Profile
 * Composer create form so the user can act before saving, instead of only
 * discovering it at compile time.
 */
export interface NameCollision {
  /** The artifact name that collides across two collections. */
  name: string;
  /** The artifact type (rule/skill/agent/...) of the colliding artifacts. */
  artifactType: string;
  /** The collection that loses the name (its artifact is overridden). */
  losingCollectionId: string;
  /** The collection that wins the name (its artifact is kept). */
  winningCollectionId: string;
  /** The losing artifact's id — what "Disable in this profile" adds to
   *  `disabled_artifact_ids`. */
  losingArtifactId: string;
}

/**
 * Detect artifact-name collisions across a composed profile, replicating
 * `compile_profile()`'s dedup step (backend/app/services/compiler.py) exactly:
 *
 * - Collections are iterated in profile order (base first, then additional in
 *   the order they appear in `additional_collection_ids`).
 * - Artifacts are deduplicated by name alone; later collections override
 *   earlier ones ("later wins").
 * - A collision is recorded only when the same name exists in two *different*
 *   collections (compared by `collection_id`, not name — two distinct
 *   collections can share a display name). Same-name artifacts within a single
 *   collection are NOT flagged, matching the backend.
 * - Artifacts whose id is in `disabledArtifactIds` are excluded from the dedup
 *   map entirely (they won't be compiled, so they can't collide) — keeping the
 *   preview consistent with what compilation actually does.
 * - Artifacts with `is_enabled === false` are also excluded, mirroring the
 *   backend's `is_enabled == True` query filter (compiler.py) — a disabled
 *   artifact is never compiled, so it can't collide.
 *
 * Pure function — no React, unit-testable in isolation.
 *
 * @param collectionIds Ordered collection ids in profile order (base first).
 * @param artifactsByCollection Map of collection id -> its artifacts.
 * @param disabledArtifactIds Artifact ids disabled for this profile.
 */
export function detectNameCollisions(
  collectionIds: string[],
  artifactsByCollection: Record<string, Artifact[]>,
  disabledArtifactIds: string[] = [],
): NameCollision[] {
  const disabled = new Set(disabledArtifactIds);
  // name -> the artifact currently winning that name (later collections win).
  const seenNames = new Map<string, Artifact>();
  const collisions: NameCollision[] = [];

  for (const collectionId of collectionIds) {
    const artifacts = artifactsByCollection[collectionId] ?? [];
    for (const artifact of artifacts) {
      if (disabled.has(artifact.id)) continue;
      if (!artifact.is_enabled) continue;

      const existing = seenNames.get(artifact.name);
      if (existing !== undefined && existing.collection_id !== artifact.collection_id) {
        collisions.push({
          name: artifact.name,
          artifactType: artifact.artifact_type,
          losingCollectionId: existing.collection_id,
          winningCollectionId: artifact.collection_id,
          losingArtifactId: existing.id,
        });
      }
      // Later wins — overwrite regardless of whether a collision was recorded.
      seenNames.set(artifact.name, artifact);
    }
  }

  return collisions;
}
