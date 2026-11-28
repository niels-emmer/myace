import { afterEach, describe, expect, it, vi } from 'vitest';
import { PreviewError, packApi } from './packApi';

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json' },
  });
}

afterEach(() => {
  vi.unstubAllGlobals();
});

describe('packApi.listAllCommunity', () => {
  it('fetches every page instead of truncating at the 100-pack page cap', async () => {
    const page = (start: number, n: number) =>
      Array.from({ length: n }, (_, i) => ({ id: `p${start + i}` }));
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(jsonResponse({ items: page(0, 100), total: 230 }))
      .mockResolvedValueOnce(jsonResponse({ items: page(100, 100), total: 230 }))
      .mockResolvedValueOnce(jsonResponse({ items: page(200, 30), total: 230 }));
    vi.stubGlobal('fetch', fetchMock);

    const items = await packApi.listAllCommunity({ sort: 'alpha' });

    expect(items).toHaveLength(230);
    expect(fetchMock).toHaveBeenCalledTimes(3);
    expect(String(fetchMock.mock.calls[1][0])).toContain('offset=100');
    expect(String(fetchMock.mock.calls[2][0])).toContain('offset=200');
  });

  it('stops after one page when everything fits', async () => {
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse({ items: [{ id: 'a' }], total: 1 }));
    vi.stubGlobal('fetch', fetchMock);

    expect(await packApi.listAllCommunity()).toHaveLength(1);
    expect(fetchMock).toHaveBeenCalledTimes(1);
  });

  it('does not loop forever when the server returns an empty page early', async () => {
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse({ items: [], total: 500 }));
    vi.stubGlobal('fetch', fetchMock);

    expect(await packApi.listAllCommunity()).toEqual([]);
    expect(fetchMock).toHaveBeenCalledTimes(1);
  });
});

describe('packApi.previewInstall', () => {
  it('requests the json format for the chosen target', async () => {
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse({ files: {}, warnings: [] }));
    vi.stubGlobal('fetch', fetchMock);

    await packApi.previewInstall('pack-1', 'claude-code');

    expect(String(fetchMock.mock.calls[0][0])).toBe(
      '/api/v1/collections/community/pack-1/install.md?target=claude-code&format=json',
    );
  });

  it.each([
    [413, /too large/i],
    [429, /too many requests/i],
  ])('explains a %i', async (status, message) => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(jsonResponse({ detail: 'x' }, status)));

    const error = await packApi.previewInstall('pack-1', 'cursor').catch((e: unknown) => e);

    expect(error).toBeInstanceOf(PreviewError);
    expect((error as PreviewError).status).toBe(status);
    expect((error as Error).message).toMatch(message);
  });

  it('passes through the server detail for other errors', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(jsonResponse({ detail: "Adapter 'x' is currently disabled" }, 400)),
    );

    await expect(packApi.previewInstall('pack-1', 'x')).rejects.toThrow(/disabled/);
  });
});
