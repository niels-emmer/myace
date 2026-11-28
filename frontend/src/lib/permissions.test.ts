import { describe, expect, it } from 'vitest';
import { agentRestrictions, isPermissionPolicy, parsePolicyRules } from './permissions';

describe('permissions helpers', () => {
  it('recognises only permissions:* model configs as policies', () => {
    expect(isPermissionPolicy({ artifact_type: 'model_config', name: 'permissions:default' })).toBe(true);
    expect(isPermissionPolicy({ artifact_type: 'model_config', name: 'model:claude' })).toBe(false);
    expect(isPermissionPolicy({ artifact_type: 'rule', name: 'permissions:default' })).toBe(false);
  });

  it('parses valid rules and drops allow, unknown effects and junk', () => {
    const body = JSON.stringify({
      rules: [
        { capability: 'execute', effect: 'ask', match: 'sudo *' },
        { capability: 'execute', effect: 'allow', match: 'ls' },
        { capability: 7, effect: 'ask' },
        'nope',
      ],
    });
    expect(parsePolicyRules(body)).toEqual([{ capability: 'execute', effect: 'ask', match: 'sudo *' }]);
  });

  it('never throws on malformed bodies', () => {
    for (const body of ['', 'not json', '{}', '{"rules": 3}', 'null']) {
      expect(parsePolicyRules(body)).toEqual([]);
    }
  });

  it('describes agent restrictions and ignores allow / absence', () => {
    expect(agentRestrictions({ edit: 'deny', execute: 'ask', read: 'allow' })).toEqual([
      'Cannot edit files',
      'Asks before it can run commands',
    ]);
    expect(agentRestrictions(null)).toEqual([]);
    expect(agentRestrictions(undefined)).toEqual([]);
  });
});
