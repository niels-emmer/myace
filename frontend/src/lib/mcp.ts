/**
 * Whether this deployment serves the read-only MCP endpoint (ADR-0018).
 *
 * The `mcp` service is opt-in (`profile: ["mcp"]` in docker-compose.yml), while
 * the frontend is a static build — so "is MCP enabled here?" cannot be answered
 * by a build-time flag. The frontend's nginx maps `/mcp/health` onto the
 * container's own liveness route (see frontend/nginx.conf); that path 502s when
 * the profile is not running, which is what this probe observes.
 *
 * The JSON body is checked, not only `res.ok`: both nginx's SPA fallback and
 * Vite's dev server answer unknown paths with index.html and a 200, so a status
 * code alone would report MCP as available on every deployment.
 */
export async function probeMcpAvailability(): Promise<boolean> {
  try {
    const response = await fetch('/mcp/health', {
      headers: { Accept: 'application/json' },
      credentials: 'same-origin',
    });
    if (!response.ok) return false;
    const body = (await response.json()) as { status?: string; server?: string };
    return body.status === 'ok' && body.server === 'myace';
  } catch {
    return false;
  }
}
