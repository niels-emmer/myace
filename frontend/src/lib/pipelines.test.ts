import { describe, it, expect } from 'vitest';
import { buildPipelineGraph, setupsForCollection } from './pipelines';
import type { Artifact, Profile } from '../types';

function agent(name: string, handoff?: string[]): Artifact {
  return {
    id: name,
    collection_id: 'collection-1',
    artifact_type: 'agent',
    name,
    version: '1.0.0',
    priority: 50,
    target_compatibility: ['claude-code'],
    tags: ['mode:subagent'],
    description: `${name} description`,
    body: '',
    file_path: `agents/${name}.md`,
    is_enabled: true,
    created_at: '2026-01-01T00:00:00Z',
    updated_at: '2026-01-01T00:00:00Z',
    handoff_to: handoff,
  };
}

function setup(overrides: Partial<Profile>): Profile {
  return {
    id: 'setup-1',
    owner_id: 'owner-1',
    name: 'My setup',
    base_collection_id: 'collection-1',
    additional_collection_ids: [],
    disabled_artifact_ids: [],
    is_public: false,
    version: 1,
    created_at: '2026-01-01T00:00:00Z',
    updated_at: '2026-01-01T00:00:00Z',
    ...overrides,
  };
}

describe('buildPipelineGraph', () => {
  const agentsByName = new Map([
    ['builder', agent('builder', ['verifier'])],
    ['verifier', agent('verifier', ['builder'])],
  ]);

  it('walks every reached agent and keeps back-edges', () => {
    const { nodes, edges } = buildPipelineGraph({
      primary: 'orchestrator',
      handoff: ['builder'],
      agentsByName,
    });

    expect(nodes.map((n) => n.id).sort()).toEqual(['builder', 'orchestrator', 'verifier']);
    expect(nodes.find((n) => n.id === 'orchestrator')?.isPrimary).toBe(true);
    expect(nodes.find((n) => n.id === 'builder')?.level).toBe(1);
    expect(nodes.find((n) => n.id === 'verifier')?.level).toBe(2);
    expect(edges.map((e) => e.id).sort()).toEqual([
      'builder->verifier',
      'orchestrator->builder',
      'verifier->builder',
    ]);
  });

  it('keeps an unresolved handoff target as a missing node', () => {
    const { nodes } = buildPipelineGraph({
      primary: 'orchestrator',
      handoff: ['ghost'],
      agentsByName,
    });
    const ghost = nodes.find((n) => n.id === 'ghost');
    expect(ghost?.isMissing).toBe(true);
    expect(ghost?.label).toBe('Ghost');
  });

  it('never marks the composed primary agent as missing', () => {
    const { nodes } = buildPipelineGraph({
      primary: 'pipeline-orchestrator',
      handoff: ['builder'],
      agentsByName,
    });
    const primary = nodes.find((n) => n.id === 'pipeline-orchestrator');
    expect(primary?.isPrimary).toBe(true);
    expect(primary?.isMissing).toBe(false);
  });
});

describe('setupsForCollection', () => {
  it('matches the starting-point pack and add-on packs', () => {
    const base = setup({ id: 'base', base_collection_id: 'pack-a' });
    const addOn = setup({ id: 'add-on', base_collection_id: 'other', additional_collection_ids: ['pack-a'] });
    const unrelated = setup({ id: 'unrelated', base_collection_id: 'pack-b' });

    expect(setupsForCollection([base, addOn, unrelated], 'pack-a').map((p) => p.id)).toEqual([
      'base',
      'add-on',
    ]);
    expect(setupsForCollection(undefined, 'pack-a')).toEqual([]);
  });
});
