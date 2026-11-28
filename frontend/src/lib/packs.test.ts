import { describe, expect, it } from 'vitest';
import {
  formatUpdated,
  frameworkLabel,
  missingLayers,
  packMatchesQuery,
  parseLibraryState,
  serializeLibraryState,
  topicFacets,
} from './packs';

describe('frameworkLabel', () => {
  it('maps adapter names and aliases to display labels', () => {
    expect(frameworkLabel('claude-code')).toBe('Claude Code');
    expect(frameworkLabel('codex-cli')).toBe('Codex CLI');
    expect(frameworkLabel('amazon-q')).toBe('Amazon Q');
    expect(frameworkLabel('pi-dev')).toBe('pi.dev');
    expect(frameworkLabel('copilot')).toBe('Copilot CLI');
  });

  it('leaves unknown targets untouched', () => {
    expect(frameworkLabel('some-future-adapter')).toBe('some-future-adapter');
  });
});

describe('library state in the URL', () => {
  it('round-trips and omits defaults', () => {
    const state = {
      search: 'go',
      facet: 'additional' as const,
      category: 'Languages & Platforms',
      topic: 'security',
      sort: 'rated' as const,
    };
    const params = serializeLibraryState(state);
    expect(parseLibraryState(params)).toEqual(state);

    const defaults = serializeLibraryState({
      search: '',
      facet: 'all',
      category: null,
      topic: null,
      sort: 'recommended',
    });
    expect(defaults.toString()).toBe('');
  });

  it('ignores garbage a user typed into the URL', () => {
    const state = parseLibraryState(new URLSearchParams('facet=nope&sort=hot&q=x'));
    expect(state).toMatchObject({ facet: 'all', sort: 'recommended', search: 'x' });
  });
});

describe('packMatchesQuery', () => {
  const pack = { name: 'Go Developer', description: 'Goroutine ownership', category: 'Languages' };

  it('matches name, description, category and topics, case-insensitively', () => {
    expect(packMatchesQuery(pack, [], 'GO DEV')).toBe(true);
    expect(packMatchesQuery(pack, [], 'goroutine')).toBe(true);
    expect(packMatchesQuery(pack, [], 'languages')).toBe(true);
    expect(packMatchesQuery(pack, ['concurrency'], 'concurrency')).toBe(true);
    expect(packMatchesQuery(pack, [], 'kubernetes')).toBe(false);
    expect(packMatchesQuery(pack, [], '   ')).toBe(true);
  });
});

describe('topicFacets', () => {
  it('keeps topics shared by two packs, most common first', () => {
    const topics = { a: ['security', 'go'], b: ['security', 'testing'], c: ['testing', 'security'] };
    expect(topicFacets(['a', 'b', 'c'], topics)).toEqual([
      { topic: 'security', count: 3 },
      { topic: 'testing', count: 2 },
    ]);
    expect(topicFacets(['a'], topics)).toEqual([]);
  });

  it('caps the number of chips', () => {
    const topics = { a: ['x1', 'x2', 'x3'], b: ['x1', 'x2', 'x3'] };
    expect(topicFacets(['a', 'b'], topics, { max: 2 })).toHaveLength(2);
  });
});

describe('formatUpdated', () => {
  it('formats a date and tolerates missing or bad input', () => {
    expect(formatUpdated('2026-11-28T10:00:00Z')).toMatch(/^Updated 28 Nov 2026$/);
    expect(formatUpdated(null)).toBeNull();
    expect(formatUpdated(undefined)).toBeNull();
    expect(formatUpdated('not a date')).toBeNull();
  });
});

describe('missingLayers', () => {
  const layers = [{ id: 'iac', name: 'IaC Expert' }];

  it('reports layered-on packs a setup lacks', () => {
    expect(missingLayers({ base_collection_id: 'b', additional_collection_ids: [] }, layers)).toEqual(
      layers,
    );
  });

  it('is empty when the pack is the base or an add-on of the setup', () => {
    expect(missingLayers({ base_collection_id: 'iac', additional_collection_ids: [] }, layers)).toEqual([]);
    expect(missingLayers({ base_collection_id: 'b', additional_collection_ids: ['iac'] }, layers)).toEqual([]);
  });
});
