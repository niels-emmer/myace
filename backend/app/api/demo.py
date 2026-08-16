"""Public demo compile endpoint.

`POST /demo/compile` is the first fully-public *data* route in this
backend beyond the documented auth-entry exception list (AGENTS.md rule
13): `/health`, `/auth/register`, `/auth/login`, `/auth/login/{provider}`,
`/auth/callback/{provider}`, `/auth/providers`. This is a deliberate,
reviewed exception, not an oversight — see
[ADR-0011](../../docs/adr/0011-public-demo-sandbox.md) and AGENTS.md rule
35 for the reasoning and the pattern to follow if a future route needs the
same treatment.

Stateless by construction: no `Depends(get_current_user)`, no DB session
dependency at all, no `owner_id`, nothing persisted. A visitor's markdown
is parsed into ephemeral in-memory `CanonicalArtifact` objects, run
through a fixed, small set of adapters, and the compiled previews are
returned directly — the request/response cycle is the entire lifetime of
that data. See docs/invariants.md's "the demo endpoint never persists"
invariant.

Scope is deliberately narrow to bound both abuse surface and response
size: rule-type artifacts only (parsed via the same `##`-section splitter
`scan_directory()` uses for AGENTS.md, `_parse_agents_md_content()`) — no
skills/agents/model-configs, no git URLs, no file uploads — compiled
through 3 adapters (claude-code, cursor, opencode), not all 11. Input is
capped at 20KB (`MAX_MARKDOWN_BYTES`, enforced by `DemoCompileRequest`'s
`field_validator`) — but that check runs only *after* FastAPI has already
buffered and JSON-parsed the whole request body, so a transport-level cap
is enforced earlier too: `app.core.body_limit.MaxBodySizeMiddleware`,
wired in `app/main.py` and scoped to this one route
(`DEMO_REQUEST_BODY_MAX_BYTES`, generously above `MAX_MARKDOWN_BYTES` to
cover JSON-escaping overhead), rejects an oversized body with 413 before
it's ever handed to FastAPI's own parsing. Requests are additionally
rate-limited to 10/minute/IP via slowapi, scoped to this route only via
the `@limiter.limit(...)` decorator — every other route keeps its
existing auth-based protection unchanged. The limiter instance and its
exception handler are wired once in `app/main.py` (`app.state.limiter` +
a custom `RateLimitExceeded` handler that matches this app's normal
`{"detail": ...}` error shape), which is required plumbing for the
decorator to raise 429s correctly; it does not add rate-limiting to any
other route.
"""

from fastapi import APIRouter, Request
from pydantic import BaseModel, field_validator
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.adapters import get_adapter
from app.models.artifact import CanonicalArtifact
from app.services.scanner import _parse_agents_md_content

router = APIRouter()

# A dedicated Limiter instance for this route only — app/main.py registers
# it on app.state.limiter and adds the RateLimitExceeded exception handler
# globally (required for @limiter.limit(...) to function at all), but no
# other route carries the @limiter.limit(...) decorator, so no other route
# is actually rate-limited by this.
limiter = Limiter(key_func=get_remote_address)

MAX_MARKDOWN_BYTES = 20 * 1024
# Transport-level cap for app.core.body_limit.MaxBodySizeMiddleware, wired
# in app/main.py. Deliberately larger than MAX_MARKDOWN_BYTES: a JSON
# string's escaped form (\uXXXX per character, worst case) can be several
# times its raw UTF-8 byte length, so a cap this close to MAX_MARKDOWN_BYTES
# would reject some legitimate 20KB-of-content requests at the transport
# layer before Pydantic's own, more precise, decoded-content check ever
# runs. This is a coarse early backstop, not the source of truth for the
# real content limit.
DEMO_REQUEST_BODY_MAX_BYTES = 128 * 1024
DEMO_TARGETS = ("claude-code", "cursor", "opencode")


class DemoCompileRequest(BaseModel):
    """Body for POST /demo/compile.

    Rule-type artifacts only — the same AGENTS.md `##`-section format the
    scanner already parses for real imports. No skills/agents/model-config
    input, no git URLs, no file uploads; this is a compile-preview demo,
    not a scan/import entry point.
    """
    markdown: str

    @field_validator("markdown")
    @classmethod
    def _cap_size(cls, v: str) -> str:
        if len(v.encode("utf-8")) > MAX_MARKDOWN_BYTES:
            raise ValueError(
                f"markdown must be at most {MAX_MARKDOWN_BYTES} bytes (got "
                f"{len(v.encode('utf-8'))})"
            )
        return v


class DemoCompileResponse(BaseModel):
    """Response for POST /demo/compile — compiled previews for a fixed,
    small set of target frameworks. Nothing here is persisted or
    associated with any user."""
    artifact_count: int
    targets: dict[str, dict[str, str]]


@router.post("/compile", response_model=DemoCompileResponse)
@limiter.limit("10/minute")
async def demo_compile(request: Request, body: DemoCompileRequest) -> DemoCompileResponse:
    """Parse visitor-supplied AGENTS.md-style markdown into rule artifacts
    (in-memory only) and compile them through DEMO_TARGETS for the public
    landing page's live demo widget. No authentication, no persistence."""
    parsed = _parse_agents_md_content(body.markdown)
    artifacts = [
        CanonicalArtifact(
            artifact_type=item["artifact_type"],
            name=item["name"],
            version=item["version"],
            target_compatibility=item["target_compatibility"],
            priority=item["priority"],
            tags=item["tags"],
            description=item["description"],
            body=item["body"],
        )
        for item in parsed
    ]

    targets: dict[str, dict[str, str]] = {}
    for target_name in DEMO_TARGETS:
        adapter = get_adapter(target_name)
        if adapter is not None:
            targets[target_name] = adapter.translate(artifacts)

    return DemoCompileResponse(artifact_count=len(artifacts), targets=targets)
