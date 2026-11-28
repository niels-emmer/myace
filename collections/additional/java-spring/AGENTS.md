# Java / Spring Developer

## Layered Architecture Discipline

<!-- myace: priority=50 tags=java,architecture -->

Maintain strict controller → service → repository layering. Controllers handle HTTP concerns only; services contain business logic; repositories handle data access. Never let a controller call a repository directly or a service return a JPA entity to a controller.

## Dependency Injection Discipline

<!-- myace: priority=50 tags=java,architecture -->

Prefer constructor injection over field injection. Keep classes focused — if a service needs more than 5-6 dependencies, it's doing too much. Use `@Configuration` classes for complex bean wiring.

## Annotations Over Magic

<!-- myace: priority=50 tags=java,architecture -->

Use Spring annotations deliberately and explicitly. `@Transactional` belongs on service-layer methods, not controllers. Put `@Cacheable` where the cached result is meaningful to the business operation (usually a service method), and keep cache keys and eviction explicit. Every annotation should have a clear, documented purpose — avoid "convention over configuration" when it hides behavior.

## Test Pyramid

<!-- myace: priority=70 tags=java,testing -->

Unit test services with JUnit + Mockito (fast, isolated). Integration test repositories with `@DataJpaTest` or `@SpringBootTest` (slower, covers real DB interaction). Controller test with `@WebMvcTest`. E2E tests cover critical user journeys only. See the `test-pyramid-spring` skill for the concrete checklist.

## Build Reproducibility

<!-- myace: priority=70 tags=java,build -->

Pin dependency versions in `pom.xml` or `build.gradle`. Prevent unexpected transitive upgrades with Gradle dependency locking, or on Maven a BOM plus Enforcer convergence rules (Maven has no native lockfile). Reproducible builds mean the same source + same deps = same binary, every time.
