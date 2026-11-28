---
name: Spring Security Configuration
description: Spring Security configuration checklist covering filter chains, authorization, method security, CSRF, CORS, password storage and tokens. Use when adding or reviewing authentication or authorization in a Spring Boot application.
version: "1.0.0"
priority: 50
compatibility: [opencode, claude-code, cursor, codex-cli, windsurf, aider, cline, continue-dev, goose, amazon-q, copilot-cli]
tags: [java, spring, security]
---
## Purpose

Keep authentication and authorization explicit, default-deny and testable.

## When to use it

When adding security to a Spring Boot service, reviewing a security configuration, or upgrading Spring Security across a major version.

## Checklist

- **Filter chain**: one or more `SecurityFilterChain` beans using the lambda DSL; `WebSecurityConfigurerAdapter` is gone. Spring Security 7 requires the lambda DSL and replaces `apply()` with `with()`, so check the migration guide when upgrading.
- **Authorization**: use `authorizeHttpRequests` with specific matchers first and `anyRequest().authenticated()` last. On recent versions prefer `PathPatternRequestMatcher`; the Ant and Mvc request matchers were removed in Spring Security 7.
- **Method security**: enable with `@EnableMethodSecurity` and use `@PreAuthorize` on service methods for object-level rules; URL rules alone do not stop an authenticated user reading someone else's record.
- **CSRF**: on by default and should stay on for cookie-session browser apps; disable only for stateless APIs authenticated by a bearer token.
- **CORS**: an explicit allow-list of origins, methods and headers; never `*` with credentials.
- **Passwords**: `PasswordEncoder` via `DelegatingPasswordEncoder` or a deliberate bcrypt, scrypt or Argon2 choice; never store or log plain text.
- **Tokens**: for APIs use the OAuth2 resource server support with issuer validation and audience checks, not hand-rolled JWT parsing; keep lifetimes short.
- **Sessions**: set stateless or session policy deliberately; regenerate the session on login (default).
- **Actuator**: expose only the endpoints needed and secure them; do not publish `env`, `heapdump` or `beans` publicly.
- **Headers**: keep the default security headers; change them with a reason.
- **Tests**: use `spring-security-test` (`@WithMockUser`, `jwt()`, `csrf()`) to prove both allowed and denied cases for each role.

## Expected output

A security configuration where every route is covered by a rule, object-level checks are in the service layer, and tests prove who can and cannot call each endpoint.
