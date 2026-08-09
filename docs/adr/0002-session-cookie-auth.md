# ADR-0002: Session cookies (not JWT/localStorage) for the web session

**Status:** Accepted

## Context

MyACE originally had no real authentication — every request carried a
hardcoded nil UUID that the backend silently mapped to one shared
placeholder account. Closing that gap meant picking a real session
mechanism for the web UI. Two mainstream options existed: a signed session
cookie (server-side session state, or a stateless signed cookie), or a
JWT issued at login and stored in the browser (typically `localStorage`),
sent as a `Bearer` header on every request.

The frontend already had unused, half-wired scaffolding for the JWT/
localStorage approach — `api.ts`'s `request()` helper read a
`myace_token` key from `localStorage` and attached it as `Bearer`, but
nothing ever populated that key. The scaffolding suggested that was the
original intended direction.

## Decision

Use a cookie-based session (Starlette `SessionMiddleware`, signed with
`APP_SECRET_KEY`) for the web UI, and keep the CLI's separate Bearer-token
mechanism (`ApiToken`, bcrypt-hashed, unrelated to the session) exactly as
it was. `get_current_user` accepts either.

## Alternatives considered

- **Finish the JWT/localStorage scaffolding** — rejected. Both dev (Vite
  proxy) and prod (nginx) already serve `/api/*` on the *same origin* as the
  frontend, which is exactly the condition under which cookie-based
  sessions work cleanly with zero CORS complication — the cross-origin
  problem JWT/localStorage is usually reached for to solve doesn't exist
  here. A token sitting in `localStorage` is also readable by any script on
  the page, which is a real XSS blast-radius difference against an
  `HttpOnly` cookie, for no offsetting benefit in this deployment shape.
- **One unified mechanism for both the web UI and the CLI** — rejected. The
  CLI has no browser, no cookie jar, and already had a working, tested
  Bearer-token flow (`myace login --token`) predating this change. Forcing
  it onto cookies would have meant a strictly worse CLI UX for no gain;
  `get_current_user` supporting both mechanisms costs a few lines and lets
  each client use what actually fits it.

## Consequences

- The half-built `myace_token`/`localStorage` scaffolding in `api.ts` was
  removed as dead code once the cookie session replaced it.
- `SessionMiddleware` is now load-bearing for two things at once: it backs
  the actual user session, *and* Authlib's OIDC login flow needs it to
  store `state`/nonce during the redirect handshake. Removing it breaks
  both — see [debugging.md](../debugging.md#oidc-login-redirects-but-nothing-happens--state-mismatch-error).
- `APP_SECRET_KEY` went from a cosmetic default to something that actually
  matters: it signs every session cookie. The app now warns at startup if
  the placeholder value is still in use outside development — see
  [SECURITY.md](../../SECURITY.md).
- Every frontend `fetch()` call must set `credentials: 'same-origin'` or
  the cookie silently isn't sent. This bit two hand-rolled `fetch()` calls
  in `ImportPage.tsx` that bypassed the shared `api.ts` helper.
