import { render } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { layoutPipeline, PipelineFlowDiagram } from './PipelineFlow';
import { ThemeProvider } from '../contexts/ThemeContext';

// @xyflow/react's <ReactFlow> measures its container via ResizeObserver, which
// jsdom doesn't implement.
class ResizeObserverStub {
  observe() {}
  unobserve() {}
  disconnect() {}
}
vi.stubGlobal('ResizeObserver', ResizeObserverStub);

function renderDiagram() {
  const { nodes, edges } = layoutPipeline(
    [
      { id: 'orchestrator', level: 0, label: 'Orchestrator', isPrimary: true },
      { id: 'builder', level: 1, label: 'Builder' },
    ],
    [{ id: 'orchestrator->builder', source: 'orchestrator', target: 'builder' }],
  );
  const { container } = render(
    <ThemeProvider>
      <PipelineFlowDiagram nodes={nodes} edges={edges} />
    </ThemeProvider>,
  );
  return container;
}

describe('PipelineFlowDiagram', () => {
  // Regression guard: React Flow drops every edge whose endpoints expose no
  // handle (`getEdgePosition()` returns null), so a custom node without
  // <Handle>s renders agents but no handoff connectors at all.
  it('renders source and target handles on every node', () => {
    const container = renderDiagram();
    expect(container.querySelectorAll('.react-flow__handle.target')).toHaveLength(2);
    expect(container.querySelectorAll('.react-flow__handle.source')).toHaveLength(2);
    expect(container.querySelectorAll('.react-flow__handle-left')).toHaveLength(2);
    expect(container.querySelectorAll('.react-flow__handle-right')).toHaveLength(2);
  });
});
