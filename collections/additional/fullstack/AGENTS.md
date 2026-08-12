# Full-Stack Developer

## Contracts Before Implementations

Agree on API contract shape (request/response schemas, error shapes, auth mechanism, pagination) before building either side. Document it in a shared location both frontend and backend reference.

## Share Types, Not Implementations

Use shared types packages or OpenAPI-to-codegen rather than duplicating Pydantic models and TypeScript interfaces. Duplicated definitions guarantee drift.

## E2E Correctness Over Layer-by-Layer Completeness

A feature isn't done until the actual HTTP path works end to end. Layer-isolated tests miss CORS misconfigs, content-type mismatches, and silently dropped fields.

## One Person, One Feature, End To End

Implement a single feature (DB → API → UI) in one pass. Splitting across "backend does the API" and "frontend picks it up later" guarantees coordination overhead and integration bugs.

## Error Boundaries On Both Sides

Every endpoint documents its failure modes; the frontend handles each explicitly (validation, not-found, server error) rather than with a generic catch-all.
