import { ReactFlow, Background, Controls, Position, MarkerType } from '@xyflow/react';
import type { Node, Edge, NodeProps } from '@xyflow/react';
import '@xyflow/react/dist/style.css';
import { HelpCircle } from 'lucide-react';

// Shared building blocks for rendering a pipeline as a flow diagram — used
// by both the Orchestration Gallery (Epic 3.3, diagramming a real,
// possibly-branching handoff_to graph) and the pipeline composition wizard
// (Epic 3.4, previewing a simple linear chain before it's saved). Layout,
// node styling, and the ReactFlow wrapper live here once so the two pages
// render pipelines identically rather than diverging.

export function formatAgentName(name: string): string {
  return name
    .split(/[-_]/)
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(' ');
}

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

export const pipelineNodeTypes = { pipelineNode: PipelineNode };

/** One entry per agent that should appear in the diagram. `level` groups
 * nodes into columns (0 = leftmost / the primary/entry agent). */
export interface PipelineNodeSpec {
  id: string;
  level: number;
  label: string;
  description?: string;
  isPrimary?: boolean;
  isMissing?: boolean;
}

export interface PipelineEdgeSpec {
  id: string;
  source: string;
  target: string;
}

/** Simple layered layout — no dagre dependency. Fine for pipelines this
 * small (a handful of agents); groups nodes by `level` into columns and
 * stacks each column's nodes vertically, centered. */
export function layoutPipeline(
  nodeSpecs: PipelineNodeSpec[],
  edgeSpecs: PipelineEdgeSpec[],
): { nodes: Node[]; edges: Edge[] } {
  const byLevel = new Map<number, PipelineNodeSpec[]>();
  for (const spec of nodeSpecs) {
    const bucket = byLevel.get(spec.level) ?? [];
    bucket.push(spec);
    byLevel.set(spec.level, bucket);
  }

  const nodes: Node[] = [];
  for (const [level, specs] of byLevel) {
    specs.forEach((spec, index) => {
      nodes.push({
        id: spec.id,
        type: 'pipelineNode',
        position: {
          x: level * 240,
          y: index * 110 - ((specs.length - 1) * 110) / 2,
        },
        data: {
          label: spec.label,
          description: spec.description,
          isPrimary: spec.isPrimary ?? false,
          isMissing: spec.isMissing ?? false,
        },
        sourcePosition: Position.Right,
        targetPosition: Position.Left,
      });
    });
  }

  const edges: Edge[] = edgeSpecs.map((spec) => ({
    id: spec.id,
    source: spec.source,
    target: spec.target,
    animated: false,
    markerEnd: { type: MarkerType.ArrowClosed },
    style: { stroke: 'var(--xf-edge-stroke, #94a3b8)', strokeWidth: 1.5 },
  }));

  return { nodes, edges };
}

export function PipelineFlowDiagram({ nodes, edges }: { nodes: Node[]; edges: Edge[] }) {
  return (
    <div className="bg-card border border-border rounded-xl h-[520px]">
      <ReactFlow
        nodes={nodes}
        edges={edges}
        nodeTypes={pipelineNodeTypes}
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
  );
}
