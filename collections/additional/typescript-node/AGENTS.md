# TypeScript / Node Developer

TypeScript and Node.js conventions for services, libraries and tooling. This collection layers on a
base collection (Software Engineer is the usual pairing) and adds the language and runtime layer. The
`frontend` collection covers UI work; this one covers the language, the Node runtime and the npm
supply chain. Without a base pack, still run the checks below before calling work done.

## TypeScript Strictness

<!-- myace: priority=70 tags=typescript,typing -->

Compile with `strict` on and keep it on. Avoid `any`; use `unknown` and narrow it. Do not silence the compiler with `as` casts, `!` non-null assertions or `@ts-ignore` unless a comment says why it is safe (prefer `@ts-expect-error`, which fails when it is no longer needed). Consider `noUncheckedIndexedAccess` for new code. See the `typescript-config-and-types` skill.

## Validate Data At The Boundary

<!-- myace: priority=90 tags=typescript,security -->

Types are erased at runtime, so a TypeScript type does not validate anything. Parse every request body, environment variable, file, message and third-party response with a runtime schema (zod, valibot, ajv or the project's own) and derive the static type from the schema. Never trust `JSON.parse(...) as Foo`.

## No Floating Promises

<!-- myace: priority=70 tags=typescript,reliability -->

Every promise is awaited, returned or explicitly handled; enable the lint rule that flags floating and misused promises. Never leave an `async` function's rejection unhandled, and do not use `async` callbacks where the caller ignores the returned promise (event handlers, `forEach`). Bound concurrency instead of `Promise.all` over unbounded input.

## Node Process And Input Safety

<!-- myace: priority=90 tags=node,security -->

Never build shell commands from input: use `execFile`/`spawn` with an argument array, not `exec` with a string. Resolve user-supplied paths against a fixed base directory and reject anything that escapes it. Do not `eval` or construct code from data, and guard against prototype pollution when merging untrusted objects. Read secrets from the environment or a secret manager, never from source, and never log them.

## Dependency And Publish Hygiene

<!-- myace: priority=90 tags=node,supply-chain -->

Commit the lockfile and install with `npm ci` (or the lockfile-honouring equivalent) in CI. Review new dependencies for need, maintenance and install scripts before adding them, and keep install-time scripts off for packages that do not need them. Publish from CI with provenance or trusted publishing rather than a long-lived token. See the `javascript-dependency-hygiene` skill.

## TypeScript Tests Run With The Code

<!-- myace: priority=70 tags=typescript,testing -->

Use the project's test runner (Vitest, Jest or `node:test`) and write a failing test first for a bug fix. Keep unit tests free of real network, clock and filesystem state. Run type check, lint, tests and build before reporting done; a passing test run with a failing `tsc` is not done.
