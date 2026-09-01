# Java / Spring Developer

## Layered Architecture Discipline

Maintain strict controller → service → repository layering. Controllers handle HTTP concerns only; services contain business logic; repositories handle data access. Never let a controller call a repository directly or a service return a JPA entity to a controller.

## Dependency Injection Discipline

Prefer constructor injection over field injection. Keep classes focused — if a service needs more than 5-6 dependencies, it's doing too much. Use `@Configuration` classes for complex bean wiring; avoid component scanning for production-critical beans.

## Annotations Over Magic

Use Spring annotations deliberately and explicitly. `@Transactional` belongs on service-layer methods, not controllers. `@Cacheable` on repository methods, not services. Every annotation should have a clear, documented purpose — avoid "convention over configuration" when it hides behavior.

## Test Pyramid

Unit test services with JUnit + Mockito (fast, isolated). Integration test repositories with `@DataJpaTest` or `@SpringBootTest` (slower, covers real DB interaction). Controller test with `@WebMvcTest`. E2E tests cover critical user journeys only. See the `test-pyramid-spring` skill for the concrete checklist.

## Build Reproducibility

Pin dependency versions in `pom.xml` or `build.gradle`. Use lockfiles (Maven Enforcer, Gradle dependency locking) to prevent unexpected transitive upgrades. Reproducible builds mean the same source + same deps = same binary, every time.
