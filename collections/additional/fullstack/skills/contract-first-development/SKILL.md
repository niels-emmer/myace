---
name: Contract-First Development
description: How to define, document, and maintain the shared contract between frontend and backend.
version: "1.0.0"
priority: 60
compatibility: [opencode, claude-code, cursor, codex-cli, windsurf, aider, cline, continue-dev, goose, amazon-q, copilot-cli]
tags: [fullstack, api, contract]
---
## Purpose

Prevent frontend-backend integration bugs by defining the contract before building either side.

## When to use it

Starting a new feature that touches both frontend and backend.

## Checklist

- **Define the contract first**: OpenAPI spec as the source of truth for request/response shapes, error codes, auth requirements, pagination.
- **Codegen**: use openapi-typescript, orval, or equivalent to generate client types from the spec.
- **Shared types package**: if not using codegen, maintain a shared package with types both sides import.
- **Contract tests**: use consumer-driven contracts (Pact) or request/response snapshot tests to catch drift.
- **Breaking change protocol**: deprecate fields before removing them; never silently rename or change types.
- **Document the contract location**: every contributor knows where to find the canonical spec.

## Expected output

A documented API contract that both frontend and backend implement against, with automated checks preventing drift.
