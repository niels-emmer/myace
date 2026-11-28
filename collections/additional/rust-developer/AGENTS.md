# Rust Developer

Rust conventions for services, libraries and CLIs. This collection layers on a base collection
(Software Engineer is the usual pairing) and adds the language layer: error types, unsafe policy,
ownership pitfalls, async behaviour and the Cargo toolchain gates. Without a base pack, still run
the checks below before calling work done.

## Rust Errors Are Typed

<!-- myace: priority=70 tags=rust,reliability -->

Return `Result` and propagate with `?`. Use a typed error (an enum, usually with `thiserror`) in libraries and `anyhow`-style context in applications. Do not use `unwrap()` or `expect()` outside tests and provably-infallible cases; where `expect` is used, the message states the invariant. Do not use panics for expected failures such as bad input.

## Rust Unsafe Is Exceptional

<!-- myace: priority=90 tags=rust,security -->

Avoid `unsafe`. Where it is unavoidable, keep the block as small as possible, put a `// SAFETY:` comment on it that states the invariant relied on and why it holds, and wrap it in a safe API. Do not add `unsafe` without calling it out for review. On the 2024 edition, unsafe operations inside an `unsafe fn` still need their own `unsafe {}` block.

## Rust Clippy And Format Gates

<!-- myace: priority=70 tags=rust,build -->

Run `cargo fmt --check`, `cargo clippy --all-targets --all-features -- -D warnings` and `cargo test` before reporting done. Fix lints rather than `#[allow]`ing them; an `#[allow]` carries a one-line reason. Set the `edition` and `rust-version` in `Cargo.toml` deliberately.

## Rust Async And Concurrency Care

<!-- myace: priority=70 tags=rust,concurrency -->

Never block inside async code: use the runtime's async APIs or `spawn_blocking` for blocking and CPU-heavy work. Do not hold a `std::sync::Mutex` guard across an `.await`. Prefer message passing or well-scoped shared state to scattered `Arc<Mutex<_>>`. Every spawned task has an owner that handles its result and its cancellation.

## Rust Dependencies And Supply Chain

<!-- myace: priority=90 tags=rust,supply-chain -->

Commit `Cargo.lock` for binaries and services. Add a dependency only when it earns its place, check its maintenance and licence, and keep default features off unless needed. Run `cargo audit` or `cargo deny` in CI for advisories, licences and duplicate versions, and triage findings instead of ignoring them. See the `rust-cargo-hygiene` skill.

## Rust Tests Run With The Code

<!-- myace: priority=70 tags=rust,testing -->

Put unit tests next to the code, integration tests in `tests/`, and examples in doc tests so they compile. Write a failing test first for a bug fix, and keep tests free of real network and clock dependence. Consider property tests for parsers and serialisers. See the `rust-testing-patterns` skill.
