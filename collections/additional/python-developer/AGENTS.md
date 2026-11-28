# Python Developer

Python-specific conventions. This collection layers on a base collection (Software Engineer
is the usual pairing) and adds the language layer: typing, packaging, testing and the
pitfalls that recur in Python services. It assumes the base pack's change-control and
secrets rules; without a base pack, still run the checks below before calling work done.

## Python Typing Discipline

<!-- myace: priority=70 tags=python,typing -->

Annotate every public function and method signature, including return types, and run a type checker (mypy or pyright) in CI at the strictness the project already uses. Prefer concrete types over `Any`; use `Protocol` or `TypedDict` for structural shapes. Never add `# type: ignore` without a code and a one-line reason. See the `python-typing-and-validation` skill.

## Python Packaging And Environments

<!-- myace: priority=70 tags=python,build -->

Declare the project in `pyproject.toml`, pin application dependencies with a lockfile (uv, pip-tools or poetry), and keep dev, test and docs dependencies in separate groups. Never `pip install` into the system interpreter, and never commit a virtualenv. Install from the lockfile in CI so the same source gives the same environment. See the `python-project-layout` skill.

## Python Error Handling

<!-- myace: priority=70 tags=python,reliability -->

Catch the narrowest exception that you can actually handle; never write a bare `except:` or swallow `Exception` without logging and re-raising. Raise domain-specific exceptions with a message that says what failed and with which input, and chain with `raise ... from err`. Do not use `assert` for runtime validation, since it is stripped under `-O`.

## Python Mutable State And Async Pitfalls

<!-- myace: priority=70 tags=python,reliability -->

Never use a mutable default argument; use `None` and create the value inside. Do not block the event loop in `async` code: no `time.sleep`, synchronous HTTP or file I/O in a coroutine, and no `await` forgotten on a coroutine. Keep module import side-effect free (no network calls, no config reads at import time).

## Python Untrusted Input And Secrets

<!-- myace: priority=90 tags=python,security -->

Treat every value from a request, file, queue or LLM as untrusted: validate it at the boundary with a schema (Pydantic, attrs or msgspec). Never build SQL, shell commands or file paths by string formatting; use parameterised queries, `subprocess.run([...])` with a list and no `shell=True`, and `pathlib` with an explicit base-directory check. Never `pickle.loads`, `yaml.load` (use `safe_load`) or `eval` data you did not produce. Keep secrets in the environment or a secret manager, never in source.

## Python Tests Run With The Code

<!-- myace: priority=70 tags=python,testing -->

Use pytest. Write a failing test first for a bug fix, keep unit tests free of network and clock dependence (inject or freeze them), and use fixtures over setup duplicated across tests. Run the linter (ruff or the project's own), formatter check and type checker alongside the tests before reporting done. See the `python-testing-patterns` skill.
