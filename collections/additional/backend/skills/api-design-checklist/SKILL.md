---
name: API Design Checklist
description: Naming, status-code, error-shape, and versioning conventions for keeping an API internally consistent as it grows.
version: "1.0.0"
priority: 50
compatibility: [opencode, claude-code, cursor, codex-cli, windsurf, aider, cline, continue-dev, goose, cody, amazon-q]
tags: [api, rest, design]
---
## Purpose

An API that's internally consistent is easier to learn, easier to generate clients for, and produces fewer "wait, why does this endpoint work differently" bugs. This skill is a checklist to run a new or changed endpoint against so it fits the shape of everything around it, rather than introducing its own one-off convention.

## When to use it

Whenever you're adding a new endpoint, changing the shape of an existing one, or reviewing someone else's API change. Also useful as a gut-check when something about an endpoint feels awkward to call — that friction is often a naming or shape inconsistency.

## Naming

- Use plural nouns for collections (`/orders`, not `/order`), and nest resources under their natural parent (`/orders/{id}/line-items`, not `/line-items?order_id=`) when the child genuinely can't exist without the parent.
- Keep casing consistent across the whole API for URL segments, query params, and JSON field names — pick one convention (commonly `kebab-case` for URLs, `snake_case` or `camelCase` for JSON body fields) and don't let a new endpoint drift to a different one.
- Use HTTP methods for verbs, not the URL — `POST /orders/{id}/cancel` is more debatable than `PATCH /orders/{id}` with a status field, but either way stay consistent with how the rest of the API expresses state transitions.

## Status codes

- `200` for a successful read or update that returns a body, `201` for a successful creation (with a `Location` header or the created resource in the body), `204` for a successful action with no body to return.
- `400` for malformed input the client sent, `401` for missing/invalid auth, `403` for authenticated-but-not-allowed, `404` for a resource that doesn't exist *or* that the caller isn't allowed to know exists, `409` for a conflict (duplicate create, concurrent-write conflict), `422` for well-formed input that fails validation rules.
- Don't overload `200` with an error payload inside it ("soft 200") — if the request failed, the status code should say so, so that generic HTTP tooling (retries, monitoring, client error handling) behaves correctly without inspecting the body.

## Error shape

- Every error response should have the same envelope shape across the whole API: a stable machine-readable error code/type, a human-readable message, and optionally a list of field-level validation errors for `422`s. Don't let different endpoints invent different error JSON shapes.
- Never include stack traces, raw exception text, database error messages, or internal file paths in an error response — see the "Fail Loud Internally, Fail Safe Externally" rule for the full reasoning.
- Make the error message actionable where possible ("`email` is required" beats "validation failed"), without revealing internal implementation detail.

## Versioning

- Decide up front how breaking changes will be signaled (a URL version prefix, a header, or a strict "additive-only, new fields are optional" policy) and apply it consistently rather than deciding ad hoc per change.
- Additive changes (new optional field, new endpoint) generally don't need a version bump. Anything that changes the meaning or removes/renames an existing field is breaking and needs the versioning mechanism, even if it feels minor.

## Expected output

A new or changed endpoint that a developer familiar with the rest of the API could predict the shape of without reading its specific docs — same naming pattern, same status code choices for equivalent situations, same error envelope, and a clear answer for whether the change is breaking.
