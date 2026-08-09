# ADR-0004: GitHub export via REST API, not a local git clone/push

**Status:** Accepted

## Context

"Export a collection to GitHub" needs to produce a real commit, on a new
branch, with a pull request opened against it. The obvious implementation
is the one every developer does by hand: clone the repo, write files,
`git add`/`commit`/`push`, then open a PR via the API. The backend already
uses `GitPython` for read-only scanning of git sources (`scan_git_repository()`),
so the tooling for a clone-based approach was already a dependency away.

## Decision

Build the commit entirely through the GitHub REST API — no local clone, no
`git` process spawned. Get the base branch's commit SHA, create blobs for
each file, build one tree, create one commit, create the new branch ref,
then open the PR. All via `httpx` (already a dependency).

## Alternatives considered

- **Local clone + `git` CLI/GitPython commit + push** — rejected. It needs
  a writable temp directory per request, real git identity configuration
  (`user.name`/`user.email`) inside the container, and credential handling
  for the push (either an embedded token in the remote URL, or a credential
  helper) — meaningfully more moving parts for a stateless backend that
  otherwise never shells out to write to an external system. It also means
  N commits' worth of filesystem I/O and process spawning per export,
  cleaned up on every code path including errors.
- **One commit per file via the Contents API
  (`PUT /repos/{owner}/{repo}/contents/{path}`)** — rejected as the simpler
  of the two REST approaches, but it produces one commit *per file* instead
  of one clean commit for the whole export, which is a worse review
  experience for the resulting PR.

## Consequences

- The backend never needs git credentials configured, a writable scratch
  directory for pushes, or `git` installed as a runtime dependency for this
  feature (it's still needed for the unrelated read-only import-from-git
  path).
- The whole operation is a handful of sequential HTTP calls
  (`backend/app/services/github_export.py`), easy to reason about and to
  test independently of any filesystem state.
- The caller's GitHub token is used for exactly one request's duration and
  never persisted or logged — see [SECURITY.md](../../SECURITY.md).
- This only works against GitHub specifically (the REST API shape is
  GitHub's, not a generic git remote). Exporting to a non-GitHub remote
  (GitLab, a bare repo) would need a different implementation, not a
  parameter change to this one.
