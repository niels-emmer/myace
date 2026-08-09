---
description: Run tests across all MyACE components (backend, frontend, CLI).
agent: general
---

Run tests for the specified MyACE component(s). Default: all components.

Usage: `/run-tests [component]`

Components:
- `backend` — Run backend tests: `cd backend && pytest`
- `frontend` — Run frontend tests: `cd frontend && npm run test`
- `cli` — Run CLI tests: `cd cli && pytest`
- `all` — Run all three (default)

For backend, also run linting and type-checking:
- `cd backend && ruff check .`
- `cd backend && mypy app`

For frontend, also run linting:
- `cd frontend && npm run lint`

Run a single test:
- Backend: `cd backend && pytest tests/test_adapters.py::test_name -v`
- Frontend: `cd frontend && npx vitest run src/components/MyComponent.test.tsx`
- CLI: `cd cli && pytest tests/test_scanner.py::test_name -v`
