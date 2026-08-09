---
description: Create a new Alembic database migration for the backend.
agent: general
---

Create a new Alembic migration for the MyACE backend.

Usage: `/add-migration <description>`

Steps:
1. Ensure the dev stack is running: `docker compose -f docker-compose.yml -f docker-compose.dev.yml ps`
2. Generate the migration: `docker compose exec backend alembic revision --autogenerate -m "<description>"`
3. Review the generated file in `backend/alembic/versions/`
4. Apply it: `docker compose exec backend alembic upgrade head`
5. Verify the migration has a working `downgrade()` function
6. Name migrations descriptively (e.g., `add_profile_visibility_column`)

Rules:
- Every schema change requires an Alembic migration
- Migrations must be reversible (`downgrade()` defined)
- Never modify a committed migration — create a new one
