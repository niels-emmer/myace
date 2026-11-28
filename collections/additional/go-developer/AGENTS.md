# Go Developer

Go conventions for services, libraries and CLIs. This collection layers on a base collection
(Software Engineer is the usual pairing) and adds the language layer: errors, contexts,
concurrency, modules and tests. Without a base pack, still run the checks below before calling
work done.

## Go Errors Are Values You Handle

<!-- myace: priority=70 tags=go,reliability -->

Check every returned error; never discard one with `_` unless a comment says why it cannot matter. Wrap with context using `fmt.Errorf("doing X: %w", err)` and compare with `errors.Is` / `errors.As`, not string matching. Return errors rather than panicking; reserve `panic` for programmer errors at startup. Do not log and return the same error.

## Go Context And Cancellation

<!-- myace: priority=70 tags=go,reliability -->

Pass `context.Context` as the first parameter of any function that does I/O or may block, and honour its cancellation. Never store a context in a struct. Set deadlines on outbound calls and call `cancel` (usually with `defer`) for every `WithCancel`/`WithTimeout`. Do not use context values for optional function parameters.

## Go Goroutine Ownership

<!-- myace: priority=70 tags=go,concurrency -->

Every goroutine has an owner that knows when it ends: use `errgroup`/`WaitGroup`, a done channel or a context, and never start one you cannot stop. Protect shared state with a mutex or confine it to one goroutine; do not share by accident. Run tests with the race detector (`go test -race`) in CI. Close channels from the sender only, and prefer bounded concurrency over one goroutine per input.

## Go Untrusted Input And Secrets

<!-- myace: priority=90 tags=go,security -->

Validate input at the boundary and use parameterised queries (`?`/`$1` placeholders), never string-built SQL. Use `exec.Command` with separate arguments and no shell, `filepath.Clean` plus a base-directory check for user-supplied paths, and `crypto/rand` rather than `math/rand` for anything secret. Set server read/write/idle timeouts on `http.Server` and limit request body size. Never log secrets or tokens.

## Go Modules And Vulnerability Checks

<!-- myace: priority=70 tags=go,build -->

Commit `go.mod` and `go.sum`, keep `go mod tidy` clean in CI, and set the `go` directive deliberately. Run `govulncheck` (or the project's equivalent) in CI and triage findings. Prefer the standard library and a small dependency set; vendor only if the project already does. See the `go-module-and-build-hygiene` skill.

## Go Tests Run With The Code

<!-- myace: priority=70 tags=go,testing -->

Write table-driven tests with named cases, use `t.Helper`, `t.Cleanup` and `t.TempDir`, and keep tests free of real network and wall-clock dependence. Write a failing test first for a bug fix. Run `gofmt`/`go vet`, the linter the project uses, and `go test -race ./...` before reporting done. See the `go-testing-patterns` skill.
