"""Local setup audit — cross-target coverage/duplicate scoring.

Backs the companion server's `POST /audit` route (`local_server.py`): given
a root directory, scans every supported target framework's conventional
config location under it, then reports where the frameworks disagree
(coverage gaps), where a single target has the same artifact defined twice
(duplicates), and a rough 0-100 score summarizing both.

`ADAPTER_EXPECTED_PATHS` is a hand-maintained mirror of each backend
adapter's own `expected_paths()` (`backend/app/adapters/*.py`) — kept in
sync by hand, not by import, since this CLI package doesn't depend on the
backend package. This is the same pattern already used for the two
parallel scanner implementations (AGENTS.md rule 8): if you change one
side, change the other.

This is a rough signal, not a certified metric. Two tiers of fidelity:

- Directories named `agents/`, `skills/`, or `commands/` (Claude Code,
  OpenCode, Codex CLI) are handed to the existing `scan_directory()` — the
  same real per-file frontmatter parsers used for local imports — pointed
  at the *parent* of the convention directory, since that's what
  `scan_directory()` itself expects to find `skills/`/`agents/`/`commands/`
  under.
- Every other directory convention (Cursor's `.cursor/rules/`, Windsurf's
  `.windsurf/rules/`, Amazon Q's `.amazonq/rules/`, Cline's `.clinerules/`,
  Continue's `.continue/rules/`+`.continue/prompts/`, Copilot's
  `.github/instructions/`, pi.dev's `.pi/prompts/`) has no shared per-file
  parser here — those frameworks each have their own frontmatter schema
  (see `docs/adapters-research.md`) and this module doesn't reimplement
  them all just to audit file presence. Every markdown/`.mdc` file directly
  inside such a directory is instead counted as one "rule" artifact named
  after its filename stem — enough to compare names/counts across targets,
  not enough to inspect real frontmatter content.

What this reliably tells you either way: which artifact names exist under
one target's expected paths but not another's, and whether a target has
the same name defined more than once. Say so in any UI that renders this,
not just here.
"""

from pathlib import Path
from typing import TypedDict

from myace_cli.scanner import _parse_agents_md_content, scan_directory

# Mirrors backend/app/adapters/*.py's expected_paths() — see module
# docstring. Directory entries end with `/`; file entries don't.
ADAPTER_EXPECTED_PATHS: dict[str, list[str]] = {
    "claude-code": ["CLAUDE.md", ".claude/agents/", ".claude/skills/", ".claude/commands/"],
    "opencode": [
        "AGENTS.md", "opencode.json",
        ".opencode/skills/", ".opencode/agents/", ".opencode/commands/",
    ],
    "cursor": [".cursor/rules/"],
    "codex-cli": ["AGENTS.md", ".agents/skills/", ".codex/agents/", ".codex/config.toml"],
    "copilot-cli": [".github/copilot-instructions.md", ".github/instructions/"],
    "cline": [".clinerules/"],
    "windsurf": [".windsurf/rules/"],
    "aider": ["CONVENTIONS.md", ".aider.conf.yml"],
    "continue": [".continue/rules/", ".continue/prompts/", "config.yaml"],
    "goose": ["AGENTS.md"],
    "amazon-q": [".amazonq/rules/"],
    "pi-dev": ["AGENTS.md", ".pi/skills/", ".pi/prompts/", ".pi/settings.json"],
}

# Plain "## section per rule" markdown files we know how to split into
# named rule artifacts. Anything else that's a single expected file
# (opencode.json, config.yaml, .aider.conf.yml, .codex/config.toml) is
# recorded as present-or-absent only — not exploded into per-name
# artifacts, since there's no shared naming convention to compare across
# targets for those formats.
_MARKDOWN_RULE_FILES = {"AGENTS.md", "CLAUDE.md", "CONVENTIONS.md"}

# Directory names scan_directory() itself understands as a convention — it
# looks for exactly these three names as subdirectories of whatever base
# path it's given. Any expected_paths() directory entry ending in one of
# these gets scan_directory()'d from its *parent*, not from itself.
_SCAN_DIRECTORY_CONVENTION_NAMES = {"agents", "skills", "commands"}


class TargetAudit(TypedDict):
    detected: bool
    artifact_count: int
    artifacts: list[dict]


class Gap(TypedDict):
    artifact_type: str
    name: str
    present_in: list[str]
    missing_from: list[str]


class Duplicate(TypedDict):
    target: str
    artifact_type: str
    name: str
    count: int


class AuditResult(TypedDict):
    path: str
    score: int
    targets: dict[str, TargetAudit]
    gaps: list[Gap]
    duplicates: list[Duplicate]


def _parse_rule_sections(path: Path) -> list[dict]:
    """Split a plain rules markdown file into one rule artifact per
    top-level '##' section, reusing `scanner._parse_agents_md_content()` —
    the exact same splitter `scan_directory()` uses for a real `AGENTS.md`
    — rather than a second, hand-copied regex. That function hardcodes
    `file_path: "AGENTS.md"` in its output (accurate for its own callers,
    which only ever pass real `AGENTS.md` content), which isn't correct
    for CLAUDE.md/CONVENTIONS.md here, so this overrides it afterward with
    the real source filename.
    """
    content = path.read_text(encoding="utf-8")
    artifacts = _parse_agents_md_content(content)
    for artifact in artifacts:
        artifact["file_path"] = path.name
    return artifacts


def scan_target(root: Path, expected_paths: list[str]) -> list[dict]:
    """Scan one target's expected_paths() locations under `root`.

    Directory-style entries (trailing `/`) named `agents/`/`skills/`/
    `commands/` are handed to the existing scan_directory() parsers, run
    from their *parent* directory (scan_directory() looks for those three
    names as subdirectories of whatever base path it's given, so pointing
    it at the leaf itself would look one level too deep). Every other
    directory convention (Cursor/Windsurf/Amazon Q/Cline/Continue/Copilot's
    flat rules-or-instructions folders) has no shared per-file parser here
    — each markdown/`.mdc` file directly inside is counted as one rule
    artifact named after its filename stem. File-style entries are parsed
    as rule sections (if a known markdown rules file) or recorded as a
    single existence marker otherwise.
    """
    artifacts: list[dict] = []
    scanned_bases: set[Path] = set()
    scanned_flat_dirs: set[Path] = set()

    for rel_path in expected_paths:
        if rel_path.endswith("/"):
            target_dir = root / rel_path.rstrip("/")
            if not target_dir.is_dir():
                continue

            if target_dir.name in _SCAN_DIRECTORY_CONVENTION_NAMES:
                base = target_dir.parent
                if base in scanned_bases:
                    continue
                scanned_bases.add(base)
                try:
                    artifacts.extend(scan_directory(base))
                except FileNotFoundError:
                    continue
            else:
                if target_dir in scanned_flat_dirs:
                    continue
                scanned_flat_dirs.add(target_dir)
                for f in sorted(target_dir.iterdir()):
                    if f.is_file() and f.suffix in (".md", ".mdc"):
                        artifacts.append({
                            "artifact_type": "rule",
                            "name": f.stem,
                            "file_path": str(f.relative_to(root)),
                        })
        else:
            target_file = root / rel_path
            if not target_file.is_file():
                continue
            if target_file.name in _MARKDOWN_RULE_FILES:
                artifacts.extend(_parse_rule_sections(target_file))
            else:
                artifacts.append({
                    "artifact_type": "model_config",
                    "name": rel_path,
                    "file_path": rel_path,
                })

    return artifacts


def _compute_score(
    detected_targets: dict[str, TargetAudit],
    names_by_target: dict[str, set[tuple[str, str]]],
    universe: set[tuple[str, str]],
    duplicates: list[Duplicate],
) -> int:
    """A deliberately simple, documented 0-100 signal — not a certified
    metric, just a rough summary of the same gaps/duplicates already
    reported in full detail elsewhere in the response. Weighted:

      - 60 pts: coverage parity. For each detected target, what fraction
        of the cross-target artifact-name "universe" does it cover? Score
        is 60 * the average of that fraction across detected targets. A
        single detected target has nothing to compare against, so it
        scores full marks here (there's no gap to measure with only one
        data point).
      - 25 pts: duplicate-free. Full marks with zero within-target
        duplicate names; -5 per duplicate found, floored at 0.
      - 15 pts: non-empty. Full marks if every detected target has at
        least one artifact; scaled down by the fraction that don't.

    Returns 0 if nothing was detected at all.
    """
    if not detected_targets:
        return 0

    if universe:
        coverage_ratios = [len(names) / len(universe) for names in names_by_target.values()]
        coverage_score = 60 * (sum(coverage_ratios) / len(coverage_ratios))
    else:
        # Nothing named was found anywhere — not rewarded as "full
        # coverage of nothing"; the non-empty component below already
        # reflects that this setup has no discoverable content.
        coverage_score = 0

    duplicate_score = max(0, 25 - 5 * len(duplicates))

    nonempty_targets = sum(1 for t in detected_targets.values() if t["artifact_count"] > 0)
    nonempty_score = 15 * (nonempty_targets / len(detected_targets))

    return round(coverage_score + duplicate_score + nonempty_score)


def audit_directory(
    root: Path,
    adapter_paths: dict[str, list[str]] | None = None,
) -> AuditResult:
    """Run the full cross-target setup audit under `root`.

    Returns the shape the companion server's `/audit` route serializes
    directly. `adapter_paths` defaults to `ADAPTER_EXPECTED_PATHS`;
    overridable for tests.
    """
    paths_by_adapter = adapter_paths if adapter_paths is not None else ADAPTER_EXPECTED_PATHS

    targets: dict[str, TargetAudit] = {}
    for name, paths in paths_by_adapter.items():
        detected = any((root / p.rstrip("/")).exists() for p in paths)
        artifacts = scan_target(root, paths) if detected else []
        targets[name] = TargetAudit(
            detected=detected, artifact_count=len(artifacts), artifacts=artifacts,
        )

    detected_targets = {name: t for name, t in targets.items() if t["detected"]}

    names_by_target: dict[str, set[tuple[str, str]]] = {
        name: {(a.get("artifact_type", "rule"), a["name"]) for a in t["artifacts"]}
        for name, t in detected_targets.items()
    }
    universe: set[tuple[str, str]] = set()
    for names in names_by_target.values():
        universe |= names

    gaps: list[Gap] = []
    for atype, name in sorted(universe):
        present_in = sorted(t for t, names in names_by_target.items() if (atype, name) in names)
        missing_from = sorted(t for t in names_by_target if t not in present_in)
        if missing_from:
            gaps.append(Gap(
                artifact_type=atype, name=name,
                present_in=present_in, missing_from=missing_from,
            ))

    duplicates: list[Duplicate] = []
    for name, t in detected_targets.items():
        counts: dict[tuple[str, str], int] = {}
        for a in t["artifacts"]:
            key = (a.get("artifact_type", "rule"), a["name"])
            counts[key] = counts.get(key, 0) + 1
        for (atype, aname), count in sorted(counts.items()):
            if count > 1:
                duplicates.append(Duplicate(
                    target=name, artifact_type=atype, name=aname, count=count,
                ))

    score = _compute_score(detected_targets, names_by_target, universe, duplicates)

    return AuditResult(
        path=str(root), score=score, targets=targets, gaps=gaps, duplicates=duplicates,
    )
