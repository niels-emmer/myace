---
description: Start the full MyACE development environment with Docker Compose.
agent: general
---

Start the MyACE development environment.

Steps:
1. Ensure `.env` exists (copy from `.env.example` if not): `cp .env.example .env`
2. Build and start the dev stack: `docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d --build`
3. Run database migrations: `docker compose exec backend alembic upgrade head`
4. Verify the backend is healthy: `curl http://localhost:8000/health`
5. Start the frontend dev server (separate terminal, for HMR): `cd frontend && npm run dev`

The dev stack gives you:
- Frontend on `http://localhost:80`
- Backend API on `http://localhost:8000`
- Backend docs at `http://localhost:8000/docs`
- Frontend HMR on `http://localhost:5173` (via `npm run dev`)
