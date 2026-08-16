"""Local companion server — lets the MyACE web UI scan this machine directly.

`myace pull`/`myace import` talk to the remote MyACE server; this instead runs
*on* the user's own machine so the web UI's Import page can trigger a real
filesystem scan without the browser needing any filesystem access of its own
(browsers can't silently walk `~/.claude`, `~/.cursor`, etc.).

Security model — why this isn't an open port any website can read from:
  1. Requires `myace login` to have already run; the allowed browser origin
     is whatever server you're logged into, not attacker-controlled.
  2. Binds to 127.0.0.1 only — never reachable off this machine.
  3. Only the logged-in server's origin is ever reflected in
     Access-Control-Allow-Origin — no wildcard, so no other page's JS can
     read a response even though the request can physically reach this port.
  4. `/scan` and `/audit` additionally require a custom `X-MyACE-Companion`
     header and an exact `Origin` match, checked server-side (not just via
     CORS response headers). A browser can't attach a custom header to a
     `no-cors` cross-origin request, so this also blocks the "blind POST
     that still causes a side effect" class of attack, not just response
     reading — and the server-side origin check means a non-browser client
     can't just skip the CORS dance to call it directly (the same crude
     defense as a CSRF token, sized to the actual threat: a malicious page
     open in the same browser, not a co-resident malicious process, which
     already has equivalent access to this user's files regardless).
     `/audit` (the Setup Audit page's cross-target coverage/duplicate scan
     — `myace_cli/audit.py`) reads more of the filesystem than `/scan` in
     one call (every known target's expected paths, not one caller-chosen
     directory), so it is not a weaker route than `/scan` — same gate,
     same origin/header requirements, no shortcuts.
  5. Implements Chrome's Private Network Access preflight
     (`Access-Control-Allow-Private-Network`) — without it, an HTTPS page
     fetching a loopback address is blocked outright in current Chrome.
"""

from pathlib import Path
from typing import Any

from myace_cli.audit import audit_directory
from myace_cli.scanner import scan_directory

COMPANION_HEADER = "x-myace-companion"
DEFAULT_PORT = 8765


def _cors_headers(allowed_origin: str, private_network: bool) -> dict[str, str]:
    headers = {
        "Access-Control-Allow-Origin": allowed_origin,
        "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
        "Access-Control-Allow-Headers": f"Content-Type, {COMPANION_HEADER}",
        "Vary": "Origin",
    }
    if private_network:
        headers["Access-Control-Allow-Private-Network"] = "true"
    return headers


def build_app(allowed_origin: str) -> Any:
    """Build the FastAPI app. Imported lazily so the base CLI install never
    needs fastapi/uvicorn — only `pip install "myace-cli[serve]"` does."""
    from fastapi import FastAPI, HTTPException, Request
    from pydantic import BaseModel
    from starlette.middleware.base import BaseHTTPMiddleware
    from starlette.responses import JSONResponse, Response

    class ScanRequestBody(BaseModel):
        path: str
        framework: str = "opencode"

    class AuditRequestBody(BaseModel):
        path: str

    class _CompanionCors(BaseHTTPMiddleware):
        async def dispatch(self, request: Request, call_next: Any) -> Response:
            origin = request.headers.get("origin")
            private_network = (
                request.headers.get("access-control-request-private-network") == "true"
            )

            if request.method == "OPTIONS":
                if origin == allowed_origin:
                    return Response(status_code=200, headers=_cors_headers(origin, private_network))
                return Response(status_code=403)

            response = await call_next(request)
            if origin == allowed_origin:
                for key, value in _cors_headers(origin, private_network).items():
                    response.headers[key] = value
            return response

    app = FastAPI(title="myace-companion", docs_url=None, redoc_url=None, openapi_url=None)
    app.add_middleware(_CompanionCors)

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok", "server": allowed_origin}

    @app.post("/scan")
    async def scan(request: Request, body: ScanRequestBody) -> JSONResponse:
        if request.headers.get(COMPANION_HEADER) != "1":
            raise HTTPException(status_code=400, detail="Missing X-MyACE-Companion header")
        if request.headers.get("origin") != allowed_origin:
            raise HTTPException(status_code=403, detail="Origin not allowed")

        try:
            artifacts = scan_directory(body.path)
        except FileNotFoundError as e:
            raise HTTPException(status_code=404, detail=str(e)) from e

        return JSONResponse(
            {
                "path": body.path,
                "framework": body.framework,
                "artifact_count": len(artifacts),
                "artifacts": artifacts,
            }
        )

    @app.post("/audit")
    async def audit(request: Request, body: AuditRequestBody) -> JSONResponse:
        """Cross-target local setup audit — same security gate as /scan
        (rule 24): companion header + exact Origin match, both checked
        server-side, not just via CORS response headers."""
        if request.headers.get(COMPANION_HEADER) != "1":
            raise HTTPException(status_code=400, detail="Missing X-MyACE-Companion header")
        if request.headers.get("origin") != allowed_origin:
            raise HTTPException(status_code=403, detail="Origin not allowed")

        root = Path(body.path).expanduser()
        if not root.exists():
            try:
                resolved = root.resolve(strict=False)
                if resolved.exists():
                    root = resolved
            except (OSError, RuntimeError):
                pass
        if not root.exists():
            raise HTTPException(status_code=404, detail=f"Directory not found: {root}")
        if not root.is_dir():
            raise HTTPException(status_code=400, detail=f"Not a directory: {root}")

        result = audit_directory(root)
        return JSONResponse(result)

    return app


def run(allowed_origin: str, port: int = DEFAULT_PORT) -> None:
    import uvicorn

    app = build_app(allowed_origin)
    uvicorn.run(app, host="127.0.0.1", port=port, log_level="warning")
