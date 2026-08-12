---
name: Spring Test Pyramid
description: Unit, integration, slice, and E2E test patterns for Spring Boot applications.
version: "1.0.0"
priority: 55
compatibility: [opencode, claude-code, cursor, codex-cli, windsurf, aider, cline, continue-dev, goose, cody, amazon-q]
tags: [java, spring, testing]
---
## Purpose

Test Spring Boot applications at the right level — fast unit tests for logic, slower integration tests for data access.

## Checklist

- **Unit tests (JUnit + Mockito)**: test service-layer logic in isolation. Mock repository and external dependencies. Fast — run in milliseconds.
- **Repository integration tests (`@DataJpaTest`)**: test custom queries, entity mappings, and constraint enforcement against a real or embedded database.
- **Controller slice tests (`@WebMvcTest`)**: test request mapping, validation, and response serialization. Mock service layer.
- **Full context tests (`@SpringBootTest`)**: use sparingly for critical end-to-end paths only. Slow — don't use for every test.
- **Coverage**: every service method has a unit test. Every custom repository query has an integration test. Every controller endpoint has a slice test for error paths.

## Expected output

A test suite where unit tests cover business logic, integration tests cover data access, and full-context tests cover only critical paths.
