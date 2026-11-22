"""Rate limiter for credential-guessing-sensitive auth routes.

A dedicated `Limiter`, separate from `app.api.demo.limiter` (the public demo
route's), so tests can switch it off without touching the demo route's own
behaviour. `app/main.py` already registers the app-wide `RateLimitExceeded`
handler that turns a breach into a `{"detail": ...}` 429 — a route only needs
the `@auth_limiter.limit(...)` decorator (and a `request: Request` parameter).

Storage is in-memory and per-process, like the demo limiter (AGENTS.md rule
36): behind N replicas the effective limit is N times the configured one.
Behind a reverse proxy the key is the forwarded client IP, which relies on
uvicorn's `--proxy-headers` *and* on `--forwarded-allow-ips` being limited to
the private ranges — with `*` a client could forge `X-Forwarded-For` and
rotate its key at will (AGENTS.md rule 27, `tests/test_forwarded_ips.py`).
"""

from slowapi import Limiter
from slowapi.util import get_remote_address

auth_limiter = Limiter(key_func=get_remote_address)

# Public storefront browsing (ADR-0014). A third dedicated instance so tests
# and operators can tune/disable anonymous community browsing independently
# of the credential-guessing auth limits and the demo route's own limiter.
# Same in-memory, per-process caveat as the other two (AGENTS.md rule 36).
storefront_limiter = Limiter(key_func=get_remote_address)
