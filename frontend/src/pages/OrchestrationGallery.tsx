import { useMemo, useState } from 'react';
import { useQuery, useQueries } from '@tanstack/react-query';
import { Workflow, GitBranch, ArrowLeft, FolderGit2, Wrench } from 'lucide-react';
import { Link } from 'react-router-dom';
import { collectionsApi } from '../lib/api';
import {
  formatAgentName,
  layoutPipeline,
  PipelineFlowDiagram,
  type PipelineNodeSpec,
  type PipelineEdgeSpec,
} from '../components/PipelineFlow';
import type { Artifact, Collection } from '../types';

// ─── Recipe discovery ───────────────────────────────────────────
//
// A "recipe" is any agent artifact with a `mode:primary` tag and a
// non-empty handoff_to — the orchestrator half of the existing
// multi-agent pipeline pattern (see collections/base/software-engineer/
// agents/orchestrator.md). Everything here is derived client-side from
// artifacts the API already exposes (Epic 3.1's handoff_to field) — no
// new backend endpoint.

interface Recipe {
  key: string;
  collectionId: string;
  collectionName: string;
  primary: Artifact;
  agentsByName: Map<string, Artifact>;
}

function buildRecipes(
  collections: Collection[],
  artifactsByCollection: Map<string, Artifact[]>,
): Recipe[] {
  const recipes: Recipe[] = [];
  for (const collection of collections) {
    const agents = artifactsByCollection.get(collection.id) ?? [];
    if (agents.length === 0) continue;
    const agentsByName = new Map(agents.map((a) => [a.name, a]));
    for (const agent of agents) {
      if (agent.tags.includes('mode:primary') && (agent.handoff_to?.length ?? 0) > 0) {
        recipes.push({
          key: `${collection.id}:${agent.name}`,
          collectionId: collection.id,
          collectionName: collection.name,
          primary: agent,
          agentsByName,
        });
      }
    }
  }
  return recipes;
}

// ─── Flow graph construction ─────────────────────────────────────
//
// BFS from the primary agent, following each visited agent's own
// handoff_to (not just the primary's) so multi-hop chains and back-edges
// (e.g. verifier -> builder on failure) both show up. A handoff_to
// target that isn't one of this collection's known agents (a dangling
// reference — see compile_profile()'s dangling_handoff warning) still
// renders as a node, just visually marked "not found" rather than
// silently dropped.

function buildFlowGraph(recipe: Recipe) {
  const levelOf = new Map<string, number>();
  const edgeSet = new Set<string>();
  const edgeSpecs: PipelineEdgeSpec[] = [];
  const queue: string[] = [recipe.primary.name];
  const expanded = new Set<string>();
  levelOf.set(recipe.primary.name, 0);

  while (queue.length > 0) {
    const current = queue.shift()!;
    if (expanded.has(current)) continue;
    expanded.add(current);
    const currentLevel = levelOf.get(current) ?? 0;
    const agent = recipe.agentsByName.get(current);
    for (const target of agent?.handoff_to ?? []) {
      const edgeKey = `${current}->${target}`;
      if (!edgeSet.has(edgeKey)) {
        edgeSet.add(edgeKey);
        edgeSpecs.push({ id: edgeKey, source: current, target });
      }
      if (!levelOf.has(target)) {
        levelOf.set(target, currentLevel + 1);
      }
      if (!expanded.has(target)) {
        queue.push(target);
      }
    }
  }

  const nodeSpecs: PipelineNodeSpec[] = Array.from(levelOf.entries()).map(([name, level]) => {
    const agent = recipe.agentsByName.get(name);
    return {
      id: name,
      level,
      label: formatAgentName(name),
      description: agent?.description,
      isPrimary: name === recipe.primary.name,
      isMissing: !agent,
    };
  });

  return layoutPipeline(nodeSpecs, edgeSpecs);
}

// ─── UI ────────────────────────────────────────────────────────

function RecipeCard({ recipe, onSelect }: { recipe: Recipe; onSelect: () => void }) {
  const stageCount = recipe.primary.handoff_to?.length ?? 0;
  return (
    <button
      onClick={onSelect}
      className="text-left bg-card border border-border rounded-xl p-5 hover:border-brand-300 hover:shadow-sm transition-all"
    >
      <div className="flex items-center gap-2 text-brand-700">
        <Workflow className="h-5 w-5" />
        <span className="text-xs font-medium uppercase tracking-wide">Recipe</span>
      </div>
      <h3 className="text-lg font-semibold text-card-foreground mt-2">
        {formatAgentName(recipe.primary.name)}
      </h3>
      {recipe.primary.description && (
        <p className="text-sm text-muted-foreground mt-1 line-clamp-2">{recipe.primary.description}</p>
      )}
      <div className="flex items-center gap-3 mt-3 text-xs text-muted-foreground">
        <span className="inline-flex items-center gap-1">
          <FolderGit2 className="h-3.5 w-3.5" /> {recipe.collectionName}
        </span>
        <span className="inline-flex items-center gap-1">
          <GitBranch className="h-3.5 w-3.5" /> {stageCount} stage{stageCount === 1 ? '' : 's'}
        </span>
      </div>
    </button>
  );
}

export default function OrchestrationGallery() {
  const [selectedKey, setSelectedKey] = useState<string | null>(null);

  const { data: ownedCollections, isLoading: loadingOwned } = useQuery({
    queryKey: ['collections'],
    queryFn: () => collectionsApi.list(),
  });

  // No dedicated backend endpoint for "every collection with a recipe" per
  // this epic's own no-new-endpoint constraint, so this scans up to 100
  // approved community collections client-side. A deployment with more
  // published collections than that would miss recipes beyond this page —
  // an acceptable v1 scale caveat, not an oversight.
  const { data: communityCollections, isLoading: loadingCommunity } = useQuery({
    queryKey: ['community-collections', { limit: 100 }],
    queryFn: () => collectionsApi.listCommunity({ limit: 100 }),
  });

  const allCollections = useMemo(() => {
    const byId = new Map<string, Collection>();
    for (const c of ownedCollections ?? []) byId.set(c.id, c);
    for (const c of communityCollections?.items ?? []) byId.set(c.id, c);
    return Array.from(byId.values());
  }, [ownedCollections, communityCollections]);

  // A collection with zero artifacts can't possibly contain a recipe —
  // skip it before the per-collection artifact fan-out fetch below rather
  // than firing a request that's guaranteed to come back empty.
  const collectionsWithArtifacts = useMemo(
    () => allCollections.filter((c) => c.artifact_count > 0),
    [allCollections],
  );

  const agentQueries = useQueries({
    queries: collectionsWithArtifacts.map((c) => ({
      queryKey: ['artifacts', c.id, 'agent'],
      queryFn: () => collectionsApi.getArtifacts(c.id, { type: 'agent' }),
      enabled: collectionsWithArtifacts.length > 0,
    })),
  });
  const agentsLoading = agentQueries.some((q) => q.isLoading);

  const recipes = useMemo(() => {
    const artifactsByCollection = new Map<string, Artifact[]>();
    collectionsWithArtifacts.forEach((c, index) => {
      artifactsByCollection.set(c.id, agentQueries[index]?.data ?? []);
    });
    return buildRecipes(collectionsWithArtifacts, artifactsByCollection);
  }, [collectionsWithArtifacts, agentQueries]);

  const selectedRecipe = recipes.find((r) => r.key === selectedKey) ?? null;
  const flowGraph = useMemo(
    () => (selectedRecipe ? buildFlowGraph(selectedRecipe) : null),
    [selectedRecipe],
  );

  const isLoading = loadingOwned || loadingCommunity || agentsLoading;

  if (selectedRecipe && flowGraph) {
    return (
      <div className="space-y-6">
        <button
          onClick={() => setSelectedKey(null)}
          className="inline-flex items-center gap-1.5 text-sm text-muted-foreground hover:text-accent-foreground"
        >
          <ArrowLeft className="h-4 w-4" /> Back to gallery
        </button>
        <div>
          <h1 className="text-2xl font-bold text-foreground flex items-center gap-2">
            <Workflow className="h-6 w-6 text-muted-foreground" />
            {formatAgentName(selectedRecipe.primary.name)}
          </h1>
          <p className="text-muted-foreground mt-1">
            From <span className="font-medium">{selectedRecipe.collectionName}</span>. Nodes are
            agents, edges are handoff direction — including back-edges (e.g. a failed check
            routing back to the builder).
          </p>
        </div>
        <PipelineFlowDiagram nodes={flowGraph.nodes} edges={flowGraph.edges} />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-start justify-between gap-4 flex-wrap">
        <div>
          <h1 className="text-2xl font-bold text-foreground flex items-center gap-2">
            <Workflow className="h-6 w-6 text-muted-foreground" />
            Orchestration Gallery
          </h1>
          <p className="text-muted-foreground mt-1">
            Multi-agent pipelines declared across your collections and the community — a primary
            agent that routes work to a sequence of specialists via <code className="font-mono text-xs bg-muted px-1 py-0.5 rounded">handoff_to</code>.
            Select one to see how it routes.
          </p>
        </div>
        <Link
          to="/orchestration/build"
          className="inline-flex items-center gap-1.5 px-4 py-2 bg-brand-600 text-white text-sm font-medium rounded-lg hover:bg-brand-700 transition-colors flex-shrink-0"
        >
          <Wrench className="h-4 w-4" /> Compose your pipeline
        </Link>
      </div>

      {isLoading ? (
        <p className="text-sm text-muted-foreground">Scanning collections for orchestration recipes...</p>
      ) : recipes.length > 0 ? (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {recipes.map((recipe) => (
            <RecipeCard key={recipe.key} recipe={recipe} onSelect={() => setSelectedKey(recipe.key)} />
          ))}
        </div>
      ) : (
        <p className="text-sm text-muted-foreground">
          No orchestration recipes found yet. A recipe is any agent with a{' '}
          <code className="font-mono text-xs bg-muted px-1 py-0.5 rounded">mode: primary</code> tag
          and a non-empty <code className="font-mono text-xs bg-muted px-1 py-0.5 rounded">handoff_to</code>{' '}
          list — the <code className="font-mono text-xs bg-muted px-1 py-0.5 rounded">software-engineer</code> starter
          collection's <code className="font-mono text-xs bg-muted px-1 py-0.5 rounded">orchestrator</code> agent is
          a good example, or use "Compose your pipeline" above to build your own.
        </p>
      )}
    </div>
  );
}
