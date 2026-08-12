# ADR-0006: Encrypted admin-editable secrets in the database

**Status:** Accepted

## Context

`docs/plans/admin-settings-menus.md`'s ADR-2 ("OIDC provider credentials
stay in env vars") reflected the System Settings page as it originally
shipped: admins could enable/disable a provider, but credentials themselves
were env-var-only, with no UI to enter or change them. That's a real
limitation for the password-reset (SMTP) and OAuth-provider-admin-UI work —
both need an admin to be able to type a secret (an SMTP password, an OAuth
client secret) into System Settings and have it take effect immediately,
without editing `.env` and restarting the container.

Storing those secrets in the database is unavoidable if the UI is going to
accept them directly. The question is how.

## Decision

Add a single symmetric encryption key (`SETTINGS_ENCRYPTION_KEY`, env-var
only — never itself stored in the database) and encrypt every
admin-editable secret with it (Fernet — AES-128-CBC + HMAC) before writing
to `system_settings`. `backend/app/core/crypto.py` provides
`encrypt_secret()`/`decrypt_secret()`; every "Update" Pydantic schema for
such a field is a plaintext write-only field (e.g. `smtp_password`) that the
route handler encrypts immediately, and every "Read" schema exposes only a
computed `{field}_set: bool` — the encrypted value itself is never returned
to a client, matching the existing "never log tokens/secrets" rule
(AGENTS.md rule 10).

## Alternatives considered

- **Plaintext in the database** — rejected: a DB dump, backup, or a future
  read-path bug would directly expose live SMTP/OAuth credentials. The
  encryption key is one more thing to manage, but it's a single env var,
  the same operational shape as `APP_SECRET_KEY`.
- **Keep secrets env-only, UI only edits non-secret fields** — this is what
  ADR-2 described, and it directly conflicts with the product requirement
  that an admin configure SMTP and OAuth providers entirely from System
  Settings, including credentials. Superseded here.
- **A managed secrets store (Vault, cloud KMS)** — rejected as disproportionate
  for a self-hostable, single-container-per-service app; would add a hard
  external dependency for a problem a single symmetric key already solves.

## Consequences

- `SETTINGS_ENCRYPTION_KEY` unset means secrets can't be *saved* via System
  Settings — `PATCH /admin/settings` 400s with a clear message rather than
  silently storing an unencryptable value. The app still starts and runs
  without it (only a startup warning), so this isn't a hard requirement for
  deployments that don't use admin-editable secrets at all.
- Losing/rotating the key makes previously-saved secrets undecryptable —
  operators must treat it like `APP_SECRET_KEY`: generate once, back it up,
  don't rotate casually. Rotating it means re-entering every admin-saved
  secret (SMTP password, OAuth client secrets) afterward.
- This pattern is now the template for any future admin-editable secret —
  encrypted column + plaintext write-only Update field + `{field}_set`
  computed Read field, not a bespoke scheme per feature.
