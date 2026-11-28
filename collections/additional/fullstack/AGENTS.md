# Full-Stack Developer

## Contracts Before Implementations

<!-- myace: priority=70 tags=fullstack,api -->

Agree on API contract shape (request/response schemas, error shapes, auth mechanism, pagination) before building either side. Document it in a shared location both frontend and backend reference.

## Share Types, Not Implementations

<!-- myace: priority=50 tags=fullstack,api -->

Use shared types packages or OpenAPI-to-codegen rather than duplicating Pydantic models and TypeScript interfaces. Duplicated definitions guarantee drift.

## E2E Correctness Over Layer-by-Layer Completeness

<!-- myace: priority=70 tags=fullstack,testing -->

A feature isn't done until the actual HTTP path works end to end. Layer-isolated tests miss CORS misconfigs, content-type mismatches, and silently dropped fields.

## One Person, One Feature, End To End

<!-- myace: priority=50 tags=fullstack,process -->

Implement a single feature (DB → API → UI) in one pass. Splitting across "backend does the API" and "frontend picks it up later" guarantees coordination overhead and integration bugs.

## Error Boundaries On Both Sides

<!-- myace: priority=70 tags=fullstack,errors -->

Every endpoint documents its failure modes; the frontend handles each explicitly (validation, not-found, server error) rather than with a generic catch-all.
