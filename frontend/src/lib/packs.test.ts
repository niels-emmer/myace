import { describe, expect, it } from 'vitest';
import { frameworkLabel } from './packs';

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
