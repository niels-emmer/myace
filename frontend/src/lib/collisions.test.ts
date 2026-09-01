import { describe, it, expect } from 'vitest';
import { detectNameCollisions } from './collisions';
import type { Artifact } from '../types';

function makeArtifact(overrides: Partial<Artifact> & { id: string; collection_id: string; name: string }): Artifact {
  return {
    artifact_type: 'agent',
    version: '1.0.0',
    priority: 50,
    target_compatibility: [],
    tags: [],
    body: '',
    file_path: 'agents/x.md',
    is_enabled: true,
    created_at: '2026-01-01T00:00:00Z',
    updated_at: '2026-01-01T00:00:00Z',
    ...overrides,
  };
}

describe('detectNameCollisions', () => {
  it('returns no collisions for a collision-free selection', () => {
    const base = makeArtifact({ id: 'a1', collection_id: 'base', name: 'builder' });
    const additional = makeArtifact({ id: 'b1', collection_id: 'add', name: 'reviewer' });
    const result = detectNameCollisions(
      ['base', 'add'],
      { base: [base], add: [additional] },
    );
    expect(result).toEqual([]);
  });

  it('flags a cross-collection collision, naming both collections and the winner', () => {
    const base = makeArtifact({ id: 'a1', collection_id: 'base', name: 'builder' });
    const additional = makeArtifact({ id: 'b1', collection_id: 'add', name: 'builder' });
    const result = detectNameCollisions(
      ['base', 'add'],
      { base: [base], add: [additional] },
    );
    expect(result).toHaveLength(1);
    expect(result[0]).toEqual({
      name: 'builder',
      artifactType: 'agent',
      losingCollectionId: 'base',
      winningCollectionId: 'add',
      losingArtifactId: 'a1',
    });
  });

  it('applies later-wins ordering: the later collection is the winner', () => {
    // Reverse the order — now 'base' comes after 'add', so 'base' wins.
    const base = makeArtifact({ id: 'a1', collection_id: 'base', name: 'builder' });
    const additional = makeArtifact({ id: 'b1', collection_id: 'add', name: 'builder' });
    const result = detectNameCollisions(
      ['add', 'base'],
      { base: [base], add: [additional] },
    );
    expect(result).toHaveLength(1);
    expect(result[0].losingCollectionId).toBe('add');
    expect(result[0].winningCollectionId).toBe('base');
    expect(result[0].losingArtifactId).toBe('b1');
  });

  it('excludes disabled artifacts from the dedup map so they cannot collide', () => {
    const base = makeArtifact({ id: 'a1', collection_id: 'base', name: 'builder' });
    const additional = makeArtifact({ id: 'b1', collection_id: 'add', name: 'builder' });
    // Disable the losing artifact (a1) — it should no longer collide.
    const result = detectNameCollisions(
      ['base', 'add'],
      { base: [base], add: [additional] },
      ['a1'],
    );
    expect(result).toEqual([]);
  });

  it('excludes is_enabled=false artifacts so they cannot collide', () => {
    const disabledInBase = makeArtifact({ id: 'a1', collection_id: 'base', name: 'builder', is_enabled: false });
    const additional = makeArtifact({ id: 'b1', collection_id: 'add', name: 'builder' });
    const result = detectNameCollisions(
      ['base', 'add'],
      { base: [disabledInBase], add: [additional] },
    );
    expect(result).toEqual([]);
  });

  it('does not flag same-name artifacts within a single collection', () => {
    const skill = makeArtifact({ id: 'a1', collection_id: 'base', name: 'code-standards', artifact_type: 'skill' });
    const rule = makeArtifact({ id: 'a2', collection_id: 'base', name: 'code-standards', artifact_type: 'rule' });
    const result = detectNameCollisions(
      ['base'],
      { base: [skill, rule] },
    );
    expect(result).toEqual([]);
  });

  it('emits one collision per distinct name, even across multiple collections', () => {
    const base = makeArtifact({ id: 'a1', collection_id: 'base', name: 'builder' });
    const add1 = makeArtifact({ id: 'b1', collection_id: 'add1', name: 'builder' });
    const add2 = makeArtifact({ id: 'c1', collection_id: 'add2', name: 'builder' });
    const result = detectNameCollisions(
      ['base', 'add1', 'add2'],
      { base: [base], add1: [add1], add2: [add2] },
    );
    // base->add1 collision, then add1->add2 collision (add2 wins overall).
    expect(result).toHaveLength(2);
    expect(result[0].winningCollectionId).toBe('add1');
    expect(result[1].winningCollectionId).toBe('add2');
  });

  it('handles a collection with no artifacts (contributes nothing)', () => {
    const base = makeArtifact({ id: 'a1', collection_id: 'base', name: 'builder' });
    const result = detectNameCollisions(
      ['base', 'empty'],
      { base: [base], empty: [] },
    );
    expect(result).toEqual([]);
  });
});
