import { ReactFlow, Background, Controls, Handle, Position, MarkerType } from '@xyflow/react';
import type { Node, Edge, NodeProps } from '@xyflow/react';
import '@xyflow/react/dist/style.css';
import { HelpCircle } from 'lucide-react';
import { useTheme } from '../contexts/ThemeContext';

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

// React Flow only draws an edge when both endpoints expose a handle it can
// anchor to (`getEdgePosition()` returns null otherwise), and a custom node
// type renders no handles of its own. Without these two `<Handle>`s every
// edge silently disappears: the diagram shows the agents but no handoff flow.
// Inline styles are deliberate — the library's handle CSS lives in
// `@layer xyflow`, which outranks Tailwind utilities in this app's layer order.
const handleStyle = {
  width: 8,
  height: 8,
  background: 'var(--xf-edge-stroke, #94a3b8)',
  border: 'none',
  pointerEvents: 'none',
} as const;

function PipelineNode({ data }: NodeProps) {
  const { label, description, isPrimary, isMissing } = data as PipelineNodeData;
  return (
    <div
      className={`relative rounded-lg border px-3 py-2 shadow-xs min-w-[140px] max-w-[200px] ${
        isMissing
          ? 'border-dashed border-destructive/50 bg-destructive/5'
          : isPrimary
          ? 'border-brand-300 bg-brand-50'
          : 'border-border bg-card'
      }`}
      title={description || (isMissing ? `${label} is not defined in this collection` : undefined)}
    >
      <Handle type="target" position={Position.Left} isConnectable={false} style={handleStyle} />
      <div
        className={`text-sm font-medium truncate ${
          isMissing ? 'text-destructive' : isPrimary ? 'text-brand-700' : 'text-card-foreground'
        }`}
      >
        {label}
      </div>
      {isMissing ? (
        <div className="text-xs text-destructive/80 flex items-center gap-1 mt-0.5">
          <HelpCircle className="h-3 w-3" /> not found
        </div>
      ) : description ? (
        <div className={`text-xs truncate mt-0.5 ${isPrimary ? 'text-brand-700/70' : 'text-muted-foreground'}`}>
          {description}
        </div>
      ) : null}
      <Handle type="source" position={Position.Right} isConnectable={false} style={handleStyle} />
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
  const { resolvedTheme } = useTheme();
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
        // @xyflow/react v13 themes its own canvas from `prefers-color-scheme`
        // unless told otherwise, so without this the diagram goes dark inside
        // a light app on a dark-mode OS (and vice versa). Follow the app theme.
        forceColorMode={resolvedTheme}
      >
        <Background gap={20} />
        <Controls showInteractive={false} />
      </ReactFlow>
    </div>
  );
}
