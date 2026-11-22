# ADR-0016: Companion direct apply — preview-then-confirm local writes

**Status:** Proposed

## Context

Until now an install ended one of two ways: the web UI produced a zip the
user unpacked manually, or the user ran `myace pull` in a terminal. Both are
correct about *what* to write but leave the browser unable to finish the
job, which is the gap the onboarding flow's install step keeps hitting.

The obvious fix — let the web page write files — is impossible: browsers
have no filesystem API for this. The existing answer for that is the local
companion server (`myace serve`), which already runs on `127.0.0.1` behind
an exact-Origin check plus a required `X-MyACE-Companion` header (AGENTS.md
rule 24) so it can scan and audit. Extending it with a write route is the
natural step, but writing to a user's machine on behalf of a web page is the
highest-risk operation in the product: a wrong path, a stale compile, or an
overwrite with no undo is expensive to reverse.

## Decision

Add two opt-in routes to the companion server:

- `POST /apply/preview` fetches the compiled profile from the configured
  MyACE server with the stored CLI credentials, resolves the install root,
  and returns a per-file diff (`added` / `changed` / `unchanged`, byte count,
  sha256) plus a single-use `preview_id`. It writes nothing.
- `POST /apply` requires that `preview_id`, `confirm: true`, and the same
  profile/target/location/root; re-fetches and re-diffs the profile; refuses
  with `409` if the diff hash changed (the digest covers both the new content
  and each file's pre-existing state, so a local edit made after the preview
  invalidates it too); backs up every file it is about to overwrite under
  `<root>/.myace-backups/<UTC timestamp>/`; then writes each file atomically
  (temp file in the destination directory + `os.replace`). It never deletes a
  file.

Both routes are disabled unless `myace serve` is started with
`--allow-apply` or `MYACE_COMPANION_ALLOW_APPLY=1`; `/health` advertises
`apply.supported` and the target list so the UI can hide the feature. They
reuse the existing loopback bind, exact-Origin check, `X-MyACE-Companion`
header requirement, and Private Network Access preflight.

`location: "project"` confines writes to a confirmed absolute project root
(default: the companion's cwd). `location: "machine"` confines writes to
the target framework's conventional home root (e.g. `~/.claude`,
`~/.config/opencode`). Every path is checked lexically
(`safe_output_path`) **and** through `resolve(strict=False)`, so symlinks
that point outside the resolved root are refused rather than written
through. Request bodies are capped at 64 KiB, compiled profiles at 500
files / 5 MiB, and preview tokens live in an in-memory registry with a
5-minute TTL and single use — nothing is persisted to disk.

## Alternatives considered

- **Keep the zip only.** No write risk, but the browser still can't finish
  an install; the user must find the download and unpack it into the right
  directory. This is the friction the phase exists to remove.
- **Keep `myace pull` only.** Already safe and scriptable, but it requires
  a terminal and a typed command at exactly the moment a non-CLI user is
  most likely to give up. Kept as the power-user path, not replaced.
- **A write endpoint with no preview or backup.** Simplest to build, and
  rejected outright: a stale or wrong compile would overwrite real config
  with no diff shown and no undo. The diff is the consent surface; the
  backup is the escape hatch.
- **Route writes through the backend server instead of the companion.**
  The backend runs on a different machine and has no filesystem access to
  the user's; this is exactly why the companion exists.
- **Auto-approve based on a hash alone, without a confirmation token.**
  A hash proves the payload did not change, not that a human saw and
  accepted it. The short-lived token ties the write to a specific preview
  a person was shown.
- **Enable writes by default.** Writing files is not the same risk class
  as scanning them; requiring an explicit flag keeps every existing
  `myace serve` invocation read-only.

## Consequences

Easier: the install step can complete in the browser with a real diff, an
explicit confirmation, and a recoverable overwrite.

Harder / given up:

- **No automatic rollback.** Backups are taken before any write, but an
  I/O failure midway through the write phase can leave a partially applied
  set. The timestamped backup directory is the documented recovery path;
  this is a deliberate simplicity trade-off, not an unnoticed gap.
- **Symlinked framework directories are refused**, even though `myace pull`
  allows them (it checks paths lexically only). Apply writes on the user's
  behalf and must be able to prove containment, so a `~/.claude` or
  `project/.claude` symlinked outside the root is an error. Users who rely
  on dotfile-repo symlinks should keep using `myace pull`.
- **Machine placement is best-effort.** Adapter output is project-relative;
  machine installs rebase it onto the framework's home root and drop a
  duplicated leading framework directory. That is exact for the common
  targets (`claude-code`, `opencode`, `cursor`, …) but not a substitute for
  a per-framework machine-layout contract. The preview shows the resolved
  paths before confirmation, so a wrong placement is visible, not silent.
- **Single-process token registry.** As with the existing rate limiter, an
  in-memory registry means the companion is a one-process tool. It already
  binds one loopback port, so this matches its deployment shape.
- **The backend must be reachable** at apply time (the companion re-fetches
  rather than trusting a cached payload), and the stored CLI token must be
  able to compile the profile — the same permission `myace pull` needs.
