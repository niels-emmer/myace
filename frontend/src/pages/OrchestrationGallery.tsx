import { useMemo, useState } from 'react';
import { useQuery, useQueries } from '@tanstack/react-query';
import { Workflow, GitBranch, ArrowLeft, FolderGit2, Layers, Wrench, Pencil } from 'lucide-react';
import { Link, useNavigate } from 'react-router-dom';
import { collectionsApi, profilesApi } from '../lib/api';
import {
  formatAgentName,
  layoutPipeline,
  PipelineFlowDiagram,
} from '../components/PipelineFlow';
import { buildPipelineGraph, setupsForCollection } from '../lib/pipelines';
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
// The BFS itself lives in `lib/pipelines.ts` so the composition wizard's
// preview renders the same graph the saved agent will have.

function recipeGraph(recipe: Recipe) {
  const { nodes, edges } = buildPipelineGraph({
    primary: recipe.primary.name,
    handoff: recipe.primary.handoff_to ?? [],
    agentsByName: recipe.agentsByName,
  });
  return layoutPipeline(nodes, edges);
}

// ─── UI ────────────────────────────────────────────────────────

function RecipeCard({ recipe, onSelect }: { recipe: Recipe; onSelect: () => void }) {
  const stageCount = recipe.primary.handoff_to?.length ?? 0;
  return (
    <button
      onClick={onSelect}
      className="text-left bg-card border border-border rounded-xl p-5 hover:border-brand-300 hover:shadow-xs transition-all"
    >
      <div className="flex items-center gap-2 text-brand-700">
        <Workflow className="h-5 w-5" />
        <span className="text-xs font-medium uppercase tracking-wide">Recipe</span>
      </div>
      <h3 className="text-lg font-semibold text-card-foreground mt-2">
        {formatAgentName(recipe.primary.name)}
      </h3>
      {recipe.primary.description && (
        <p className="text-sm text-muted-foreground mt-1 line-clamp-4">{recipe.primary.description}</p>
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
  const navigate = useNavigate();

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

  // A pipeline's "destination setup" isn't persisted anywhere — derive it from
  // the user's own setups (same helper the composition wizard prefills from).
  const { data: profiles, isLoading: loadingProfiles } = useQuery({
    queryKey: ['profiles'],
    queryFn: () => profilesApi.list(),
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
    () => (selectedRecipe ? recipeGraph(selectedRecipe) : null),
    [selectedRecipe],
  );

  const pipelineSetups = useMemo(
    () => (selectedRecipe ? setupsForCollection(profiles, selectedRecipe.collectionId) : []),
    [profiles, selectedRecipe],
  );

  const isLoading = loadingOwned || loadingCommunity || agentsLoading;

  if (selectedRecipe && flowGraph) {
    return (
      <div className="space-y-6">
        <div className="flex items-center justify-between gap-4 flex-wrap">
          <button
            onClick={() => setSelectedKey(null)}
            className="inline-flex items-center gap-1.5 text-sm text-muted-foreground hover:text-accent-foreground"
          >
            <ArrowLeft className="h-4 w-4" /> Back to pipelines
          </button>
          <button
            onClick={() =>
              navigate('/packs/pipelines/new', {
                state: {
                  editRecipe: {
                    collectionId: selectedRecipe.collectionId,
                    collectionName: selectedRecipe.collectionName,
                    primary: selectedRecipe.primary,
                  },
                },
              })
            }
            className="inline-flex items-center gap-1.5 px-4 py-2 bg-brand-600 text-white text-sm font-medium rounded-lg hover:bg-brand-700 transition-colors shrink-0"
          >
            <Pencil className="h-4 w-4" /> Edit pipeline
          </button>
        </div>
        <div>
          <h1 className="text-2xl font-bold text-foreground flex items-center gap-2">
            <Workflow className="h-6 w-6 text-muted-foreground" />
            {formatAgentName(selectedRecipe.primary.name)}
          </h1>
          <p className="text-muted-foreground mt-1">
            Nodes are agents, edges are the handoff direction each agent declares — including
            back-edges (e.g. a failed check routing work back to the builder).
          </p>
        </div>

        <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
          <div className="rounded-xl border border-border bg-card p-4">
            <div className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
              Pack
            </div>
            <Link
              to={`/packs/${selectedRecipe.collectionId}`}
              className="mt-1 inline-flex items-center gap-1.5 text-sm font-medium text-foreground hover:underline"
            >
              <FolderGit2 className="h-4 w-4 text-muted-foreground" />
              {selectedRecipe.collectionName}
            </Link>
          </div>

          <div className="rounded-xl border border-border bg-card p-4">
            <div className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
              Destination setup
            </div>
            {loadingProfiles ? (
              <p className="mt-1 text-sm text-muted-foreground">Checking your setups…</p>
            ) : pipelineSetups.length > 0 ? (
              <>
                <Link
                  to={`/setups/${pipelineSetups[0].id}`}
                  className="mt-1 inline-flex items-center gap-1.5 text-sm font-medium text-foreground hover:underline"
                >
                  <Layers className="h-4 w-4 text-muted-foreground" />
                  {pipelineSetups[0].name}
                </Link>
                {pipelineSetups.length > 1 && (
                  <p className="mt-1 text-xs text-muted-foreground">
                    Also used by {pipelineSetups.length - 1} other setup
                    {pipelineSetups.length - 1 === 1 ? '' : 's'}
                  </p>
                )}
              </>
            ) : (
              <>
                <p className="mt-1 text-sm text-muted-foreground">Not part of a setup yet.</p>
                <Link
                  to={`/packs/${selectedRecipe.collectionId}`}
                  className="mt-1 inline-flex text-xs font-medium text-brand-700 hover:underline"
                >
                  Add this pack to a setup
                </Link>
              </>
            )}
          </div>

          <div className="rounded-xl border border-border bg-card p-4">
            <div className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
              Flow
            </div>
            <div className="mt-1 inline-flex items-center gap-1.5 text-sm font-medium text-foreground">
              <GitBranch className="h-4 w-4 text-muted-foreground" />
              {flowGraph.nodes.length} agent{flowGraph.nodes.length === 1 ? '' : 's'} ·{' '}
              {flowGraph.edges.length} handoff{flowGraph.edges.length === 1 ? '' : 's'}
            </div>
          </div>
        </div>

        <PipelineFlowDiagram nodes={flowGraph.nodes} edges={flowGraph.edges} />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="space-y-4">
        <div className="flex items-start justify-between gap-4">
          <h1 className="text-2xl font-bold text-foreground flex items-center gap-2">
            <Workflow className="h-6 w-6 text-muted-foreground" />
            Pipelines
          </h1>
          <Link
            to="/packs/pipelines/new"
            className="inline-flex items-center gap-1.5 px-4 py-2 bg-brand-600 text-white text-sm font-medium rounded-lg hover:bg-brand-700 transition-colors shrink-0"
          >
            <Wrench className="h-4 w-4" /> Compose your pipeline
          </Link>
        </div>
        <div className="max-w-3xl space-y-2 text-muted-foreground">
          <p>
            A pipeline is how a pack's agents work as a team: one entry-point agent (tagged{' '}
            <code className="font-mono text-xs bg-muted px-1 py-0.5 rounded">mode: primary</code>)
            takes each request and hands it to the right specialists through its{' '}
            <code className="font-mono text-xs bg-muted px-1 py-0.5 rounded">handoff_to</code> list —
            build, verify, review, document — and a failed check routes the work back to the agent
            that has to fix it.
          </p>
          <p>
            Nothing extra is stored: a pipeline is read from the agents in your packs and the
            community, so changing an agent's handoffs changes its pipeline. Open one to see how work
            would flow through it, or compose a straight-line pipeline from the agents in one of your
            setups.
          </p>
        </div>
      </div>

      {isLoading ? (
        <p className="text-sm text-muted-foreground">Scanning packs for pipelines…</p>
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
          pack's <code className="font-mono text-xs bg-muted px-1 py-0.5 rounded">orchestrator</code> agent is
          a good example, or use "Compose your pipeline" above to build your own.
        </p>
      )}
    </div>
  );
}
