/**
 * Pipeline derivation shared by the Pipelines gallery and the composition
 * wizard (AGENTS.md rule 34) — everything here is derived client-side from
 * artifacts and setups the API already exposes, no dedicated backend endpoint.
 *
 * Both pages must build their diagram through `buildPipelineGraph()`: the
 * gallery renders a saved agent's real handoff graph, and the wizard previews
 * the graph the agent it is about to save will have. Building the preview as
 * a separate synthetic chain made the two diagrams disagree about the same
 * pipeline.
 */
import type { Artifact, Profile } from '../types';
import type { PipelineEdgeSpec, PipelineNodeSpec } from '../components/PipelineFlow';
import { formatAgentName } from '../components/PipelineFlow';

export interface PipelineGraphInput {
  /** Name of the entry-point agent — a saved `mode: primary` agent, or the slug being composed. */
  primary: string;
  /** The entry-point agent's own handoff targets. */
  handoff: string[];
  /** Every agent the graph can resolve, by name. */
  agentsByName: Map<string, Artifact>;
}

/**
 * BFS from the entry-point agent, following each visited agent's own
 * `handoff_to` (not just the primary's) so multi-hop chains and back-edges
 * (e.g. verifier -> builder on failure) both show up. A target that isn't a
 * known agent (a dangling reference — see compile_profile()'s
 * dangling_handoff warning) still becomes a node, visually marked "not found"
 * rather than silently dropped.
 */
export function buildPipelineGraph({
  primary,
  handoff,
  agentsByName,
}: PipelineGraphInput): { nodes: PipelineNodeSpec[]; edges: PipelineEdgeSpec[] } {
  const levelOf = new Map<string, number>([[primary, 0]]);
  const edges: PipelineEdgeSpec[] = [];
  const seenEdges = new Set<string>();
  const queue: string[] = [primary];
  const expanded = new Set<string>();

  while (queue.length > 0) {
    const current = queue.shift()!;
    if (expanded.has(current)) continue;
    expanded.add(current);
    const currentLevel = levelOf.get(current) ?? 0;
    // The primary's targets come from the caller (a saved agent's handoff_to,
    // or the sequence being composed) so the wizard can preview an unsaved
    // agent whose artifact doesn't exist yet.
    const targets =
      current === primary ? handoff : (agentsByName.get(current)?.handoff_to ?? []);
    for (const target of targets) {
      const edgeId = `${current}->${target}`;
      if (!seenEdges.has(edgeId)) {
        seenEdges.add(edgeId);
        edges.push({ id: edgeId, source: current, target });
      }
      if (!levelOf.has(target)) {
        levelOf.set(target, currentLevel + 1);
      }
      if (!expanded.has(target)) {
        queue.push(target);
      }
    }
  }

  const nodes: PipelineNodeSpec[] = Array.from(levelOf.entries()).map(([name, level]) => {
    const agent = agentsByName.get(name);
    return {
      id: name,
      level,
      label: formatAgentName(name),
      description: agent?.description,
      isPrimary: name === primary,
      // The composed entry-point agent isn't saved yet, so it is never
      // "missing" — only unresolved handoff targets are.
      isMissing: name !== primary && !agent,
    };
  });

  return { nodes, edges };
}

/**
 * Setups whose pack list contains `collectionId`, as either the starting
 * point or an add-on. Nothing persists a pipeline's destination setup, so
 * both pipeline pages derive it from the user's setups to stay consistent.
 */
export function setupsForCollection(
  profiles: Profile[] | undefined,
  collectionId: string,
): Profile[] {
  return (profiles ?? []).filter(
    (profile) =>
      profile.base_collection_id === collectionId ||
      profile.additional_collection_ids.includes(collectionId),
  );
}
