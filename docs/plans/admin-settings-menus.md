# Plan: Admin/System Settings Menus

**Status: Shipped.** The `UserSettings.tsx`/`SystemSettings.tsx` split, the
`system_settings` table + migration, and MFA/TOTP endpoints all exist as
described below. See the `system_settings` table entry in
[data-model.md](../data-model.md) for the current schema. Kept here as
historical design record, not a live task list.

## Overview

Split the current monolithic Settings page into two separate concerns:
- **User Settings** (`/settings`) — profile, password, email, MFA, API tokens, appearance, CLI setup
- **System Settings** (`/admin/system`) — auth provider config, MFA enforcement, doc cache, users, adapters

## Branch

`feat/admin-settings-menus`

## Architecture Decisions

### ADR-1: System settings stored in DB, not env vars
- A new `system_settings` table (single-row) stores runtime-configurable settings
- Env vars remain for initial bootstrap and sensitive credentials
- The UI reads/writes from the DB; env vars are the fallback

### ADR-2: OIDC provider credentials stay in env vars
- Client secrets are sensitive and should not be stored in the DB unencrypted
- The system settings page shows which providers are configured (from env) and allows toggling them on/off
- Links to setup documentation are shown for each provider
- Future: encrypted credential storage in DB for full UI-based configuration

### ADR-3: TOTP for MFA (not WebAuthN in this iteration)
- `pyotp` library for TOTP generation/verification
- QR code display for authenticator app setup
- WebAuthN (passkeys) noted as future enhancement
- MFA enforcement toggle in system settings

### ADR-4: Soft-delete for account deletion
- User account deletion sets `is_active = False` and `deleted_at`
- All owned resources (collections, profiles, tokens) are soft-deactivated
- Follows existing soft-delete pattern in the codebase

## Epics

### Epic 1: Backend — System Settings Model & API
**Files:**
- `backend/app/models/system_settings.py` — new model
- `backend/app/api/admin.py` — new admin router
- `backend/app/models/__init__.py` — export new model
- `backend/app/main.py` — register admin router
- `backend/alembic/versions/` — new migration

**Tasks:**
1. Create `SystemSettings` SQLModel with single-row pattern (id=1 PK)
2. Fields: provider enable flags, MFA settings, registration toggle, doc cache TTL
3. Create admin-only CRUD API at `/api/v1/admin/settings`
4. Register router in main.py
5. Create Alembic migration
6. Write tests

### Epic 2: Backend — User Settings (Profile, Password, Email, Deletion)
**Files:**
- `backend/app/api/auth.py` — extend with new endpoints
- `backend/app/models/user.py` — add schemas

**Tasks:**
1. `PATCH /api/v1/auth/me` — update display_name, email
2. `POST /api/v1/auth/me/password` — change password (requires current password)
3. `DELETE /api/v1/auth/me` — soft-delete account + all owned data
4. Write tests

### Epic 3: Backend — OIDC Provider Toggle via System Settings
**Files:**
- `backend/app/api/admin.py` — extend settings schema
- `backend/app/core/security.py` — dynamic provider registration
- `backend/app/api/auth.py` — check provider enabled status

**Tasks:**
1. Add provider enable/disable to system settings schema
2. Make OAuth client registration check DB settings
3. Auth endpoints check if provider is enabled before allowing login
4. Write tests

### Epic 4: Backend — TOTP MFA Support
**Files:**
- `backend/app/models/user.py` — add totp fields
- `backend/app/api/auth.py` — add MFA endpoints
- `backend/app/core/deps.py` — MFA check in auth flow
- `backend/pyproject.toml` — add `pyotp` dependency
- `backend/alembic/versions/` — new migration

**Tasks:**
1. Add `pyotp` dependency
2. Add `totp_secret`, `mfa_enabled` fields to User model
3. `POST /api/v1/auth/me/mfa/totp/setup` — generate secret, return QR URI
4. `POST /api/v1/auth/me/mfa/totp/verify` — verify code, enable MFA
5. `POST /api/v1/auth/me/mfa/totp/disable` — disable MFA
6. Modify login flow: if user has MFA enabled, return `mfa_required` flag
7. `POST /api/v1/auth/mfa/verify` — verify TOTP code after password login
8. System settings: `mfa_enabled` (master switch), `mfa_forced` (require for all)
9. Write tests

### Epic 5: Frontend — System Settings Page
**Files:**
- `frontend/src/pages/SystemSettings.tsx` — new page
- `frontend/src/lib/api.ts` — add admin API methods
- `frontend/src/types/index.ts` — add types

**Tasks:**
1. Create SystemSettings page with sections:
   - Auth Providers (enable/disable, doc links)
   - MFA Settings (enable/force toggle)
   - Registration toggle
   - Doc Cache management (moved from old Settings)
   - User management (moved from old Settings)
   - Adapter registry (moved from old Settings)
2. Add admin API methods to api.ts
3. Add TypeScript types

### Epic 6: Frontend — User Settings Page
**Files:**
- `frontend/src/pages/UserSettings.tsx` — new page
- `frontend/src/lib/api.ts` — add user settings API methods
- `frontend/src/types/index.ts` — add types

**Tasks:**
1. Create UserSettings page with sections:
   - Profile (display name, email)
   - Password change
   - MFA setup (if system enables it)
   - API Tokens (moved from old Settings)
   - Appearance (moved from old Settings)
   - CLI Setup (moved from old Settings)
   - Account deletion (with confirmation modal)
2. Add user settings API methods to api.ts
3. Add TypeScript types

### Epic 7: Frontend — Menu Restructuring
**Files:**
- `frontend/src/components/Layout.tsx` — update nav items
- `frontend/src/App.tsx` — add routes

**Tasks:**
1. Add "System" nav item (admin only) pointing to `/admin/system`
2. Keep "Settings" nav item pointing to `/settings`
3. Add routes for both pages
4. Ensure admin-only routes redirect non-admins

## Verification Strategy

### Per-Epic Testing
- Backend: pytest with httpx AsyncClient (in-memory SQLite)
- Frontend: manual verification (no frontend tests exist yet)
- Each epic includes tests for happy path, error paths, and auth enforcement

### Security Audit
- All admin endpoints use `Depends(require_admin)`
- All user settings endpoints use `Depends(get_current_user)` with ownership check
- Account deletion is soft-delete only
- MFA secrets are stored encrypted
- No secrets in logs or responses

### Documentation
- Update `README.md` with new settings pages
- Update `AGENTS.md` with new API endpoints and patterns
- Update `docs/data-model.md` with new tables/fields

## Dependencies to Add

- `pyotp` — TOTP generation and verification (MIT license, actively maintained)
- `qrcode` — QR code generation for TOTP setup (MIT license)

## Risk Assessment

| Risk | Mitigation |
|------|-----------|
| OIDC provider toggle breaks existing sessions | Toggle only affects new logins, not active sessions |
| MFA lockout | Admin can disable MFA for a user via system settings |
| Account deletion data loss | Soft-delete only; admin can restore |
| Migration conflicts | Single migration per epic, tested against fresh DB |
