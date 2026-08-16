"""ASGI-level request body size cap for specific (method, path) routes.

Starlette/FastAPI buffer and JSON-parse an entire request body before any
route-level validation — including a Pydantic `field_validator` — ever
runs. A size check inside a Pydantic model (as `app.api.demo`'s
`DemoCompileRequest` originally had, alone) only rejects an oversized
payload *after* the whole thing has already been read into memory. That
gap matters specifically for `POST /demo/compile` (see
`docs/adr/0011-public-demo-sandbox.md`): it's the one fully-public,
unauthenticated route in this backend, so without a cap enforced at the
transport layer, a client could send an arbitrarily large body with no
in-memory ceiling before Pydantic ever gets a look at it — undermining the
"bounded abuse surface" claim that route's own design rests on.

This middleware wraps the raw ASGI `receive()` callable (not
`starlette.middleware.base.BaseHTTPMiddleware`, which itself needs
`await request.body()` to inspect a request — fully buffering it first
and defeating the purpose) so it can reject a request once its
actual received-so-far byte count exceeds the configured cap, without
ever holding more than roughly that many bytes in memory. It checks
actual received bytes as they stream in, not `Content-Length` alone
(which a client can omit, lie about, or which doesn't exist at all under
chunked transfer encoding).

Scoped to specific `(method, path)` pairs passed in by the caller — every
other route is completely unaffected, matching the same
don't-apply-globally pattern as `app.api.demo`'s per-route `slowapi` rate
limiter (AGENTS.md rule 36).
"""

from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Message, Receive, Scope, Send


class MaxBodySizeMiddleware:
    """Reject with 413 once a matched request's body exceeds its configured
    byte cap, checked incrementally as chunks arrive."""

    def __init__(self, app: ASGIApp, limits: dict[tuple[str, str], int]) -> None:
        self.app = app
        self.limits = limits

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        max_bytes = self.limits.get((scope["method"], scope["path"]))
        if max_bytes is None:
            await self.app(scope, receive, send)
            return

        buffered: list[Message] = []
        total = 0

        while True:
            message = await receive()
            buffered.append(message)

            if message["type"] == "http.request":
                total += len(message.get("body", b""))
                if total > max_bytes:
                    response = JSONResponse(
                        {
                            "detail": (
                                f"Request body exceeds the {max_bytes}-byte limit "
                                "for this route."
                            )
                        },
                        status_code=413,
                    )
                    await response(scope, receive, send)
                    return
                if not message.get("more_body", False):
                    break
            elif message["type"] == "http.disconnect":
                break

        # Body fully buffered (bounded by max_bytes, plus at most one
        # over-the-limit chunk we already rejected above) and within the
        # cap — replay the buffered messages to the downstream app so
        # FastAPI's own body parsing sees the exact same stream it would
        # have without this middleware in front of it.
        index = 0

        async def replay_receive() -> Message:
            nonlocal index
            if index < len(buffered):
                msg = buffered[index]
                index += 1
                return msg
            return await receive()

        await self.app(scope, replay_receive, send)
