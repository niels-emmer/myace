import { useMemo, useState } from 'react';
import { useQuery, useQueries } from '@tanstack/react-query';
import { ReactFlow, Background, Controls, Position, MarkerType } from '@xyflow/react';
import type { Node, Edge, NodeProps } from '@xyflow/react';
import '@xyflow/react/dist/style.css';
import { Workflow, GitBranch, ArrowLeft, HelpCircle, FolderGit2 } from 'lucide-react';
import { collectionsApi } from '../lib/api';
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

function formatAgentName(name: string): string {
  return name
    .split(/[-_]/)
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(' ');
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

interface FlowGraph {
  nodes: Node[];
  edges: Edge[];
}

function buildFlowGraph(recipe: Recipe): FlowGraph {
  const levelOf = new Map<string, number>();
  const edgeSet = new Set<string>();
  const edges: Edge[] = [];
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
        edges.push({
          id: edgeKey,
          source: current,
          target,
          animated: false,
          markerEnd: { type: MarkerType.ArrowClosed },
          style: { stroke: 'var(--xf-edge-stroke, #94a3b8)', strokeWidth: 1.5 },
        });
      }
      if (!levelOf.has(target)) {
        levelOf.set(target, currentLevel + 1);
      }
      if (!expanded.has(target)) {
        queue.push(target);
      }
    }
  }

  // Group by level for a simple layered layout (no dagre dependency —
  // pipelines here are small enough that this reads fine).
  const byLevel = new Map<number, string[]>();
  for (const [name, level] of levelOf) {
    const bucket = byLevel.get(level) ?? [];
    bucket.push(name);
    byLevel.set(level, bucket);
  }

  const nodes: Node[] = [];
  for (const [level, names] of byLevel) {
    names.forEach((name, index) => {
      const agent = recipe.agentsByName.get(name);
      nodes.push({
        id: name,
        type: 'pipelineNode',
        position: {
          x: level * 240,
          y: index * 110 - ((names.length - 1) * 110) / 2,
        },
        data: {
          label: formatAgentName(name),
          description: agent?.description,
          isPrimary: name === recipe.primary.name,
          isMissing: !agent,
        },
        sourcePosition: Position.Right,
        targetPosition: Position.Left,
      });
    });
  }

  return { nodes, edges };
}

// ─── UI ────────────────────────────────────────────────────────

interface PipelineNodeData {
  label: string;
  description?: string;
  isPrimary: boolean;
  isMissing: boolean;
  [key: string]: unknown;
}

function PipelineNode({ data }: NodeProps) {
  const { label, description, isPrimary, isMissing } = data as PipelineNodeData;
  return (
    <div
      className={`rounded-lg border px-3 py-2 shadow-sm min-w-[140px] max-w-[200px] ${
        isMissing
          ? 'border-dashed border-destructive/50 bg-destructive/5'
          : isPrimary
          ? 'border-brand-300 bg-brand-50'
          : 'border-border bg-card'
      }`}
      title={description || (isMissing ? `${label} is not defined in this collection` : undefined)}
    >
      <div className={`text-sm font-medium truncate ${isMissing ? 'text-destructive' : 'text-card-foreground'}`}>
        {label}
      </div>
      {isMissing ? (
        <div className="text-xs text-destructive/80 flex items-center gap-1 mt-0.5">
          <HelpCircle className="h-3 w-3" /> not found
        </div>
      ) : description ? (
        <div className="text-xs text-muted-foreground truncate mt-0.5">{description}</div>
      ) : null}
    </div>
  );
}

const nodeTypes = { pipelineNode: PipelineNode };

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

  const agentQueries = useQueries({
    queries: allCollections.map((c) => ({
      queryKey: ['artifacts', c.id, 'agent'],
      queryFn: () => collectionsApi.getArtifacts(c.id, { type: 'agent' }),
      enabled: allCollections.length > 0,
    })),
  });
  const agentsLoading = agentQueries.some((q) => q.isLoading);

  const recipes = useMemo(() => {
    const artifactsByCollection = new Map<string, Artifact[]>();
    allCollections.forEach((c, index) => {
      artifactsByCollection.set(c.id, agentQueries[index]?.data ?? []);
    });
    return buildRecipes(allCollections, artifactsByCollection);
  }, [allCollections, agentQueries]);

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
        <div className="bg-card border border-border rounded-xl h-[520px]">
          <ReactFlow
            nodes={flowGraph.nodes}
            edges={flowGraph.edges}
            nodeTypes={nodeTypes}
            nodesDraggable={false}
            nodesConnectable={false}
            elementsSelectable={false}
            panOnScroll
            zoomOnScroll={false}
            fitView
            proOptions={{ hideAttribution: true }}
          >
            <Background gap={20} />
            <Controls showInteractive={false} />
          </ReactFlow>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
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
          a good example.
        </p>
      )}
    </div>
  );
}
