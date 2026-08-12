---
name: Layered Architecture
description: Controller → service → repository layering, DTO boundaries, @Transactional placement, and exception hierarchy.
version: "1.0.0"
priority: 60
compatibility: [opencode, claude-code, cursor, codex-cli, windsurf, aider, cline, continue-dev, goose, cody, amazon-q]
tags: [java, spring, architecture]
---
## Purpose

Prevent architectural drift in Spring Boot applications by enforcing clear layer boundaries.

## Checklist

- **Controller layer**: handles HTTP concerns only (request mapping, validation, response serialization). Never contains business logic or data access.
- **Service layer**: contains business logic and transaction boundaries. Never returns JPA entities to controllers — use DTOs or projections.
- **Repository layer**: data access only. Spring Data JPA repositories or custom DAO implementations. Never contains business logic.
- **DTO boundaries**: controllers receive request DTOs and return response DTOs. Services receive and return domain objects or DTOs. Entities never cross the controller boundary.
- **@Transactional**: on service-layer methods, not controllers. Read-only transactions for query methods.
- **Exception hierarchy**: domain exceptions (extending `RuntimeException`) caught at the controller boundary and mapped to appropriate HTTP status codes via `@ControllerAdvice`.

## Expected output

A Spring Boot application where each layer has a single responsibility, entities never reach controllers, and exceptions are consistently mapped to HTTP responses.
