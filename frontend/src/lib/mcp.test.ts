import { afterEach, describe, expect, it, vi } from 'vitest';
import { probeMcpAvailability } from './mcp';

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json' },
  });
}

describe('probeMcpAvailability', () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it('reports available only for the MCP liveness body', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(jsonResponse({ status: 'ok', server: 'myace' })));

    expect(await probeMcpAvailability()).toBe(true);
  });

  it('treats the SPA fallback index.html as unavailable', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(
        new Response('<!doctype html><html></html>', {
          status: 200,
          headers: { 'Content-Type': 'text/html' },
        }),
      ),
    );

    expect(await probeMcpAvailability()).toBe(false);
  });

  it('treats a 502 from an unstarted mcp profile as unavailable', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response('Bad Gateway', { status: 502 })));

    expect(await probeMcpAvailability()).toBe(false);
  });

  it('treats a network failure as unavailable', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new TypeError('Failed to fetch')));

    expect(await probeMcpAvailability()).toBe(false);
  });
});
