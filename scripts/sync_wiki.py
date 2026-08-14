#!/usr/bin/env python3
"""Mirror docs/ into the GitHub Wiki.

docs/ is the single source of truth (edited in the same PR as the code it
describes, per AGENTS.md rule 14) — this script is the only thing that is
ever supposed to write to the Wiki. Never hand-edit a Wiki page; edit the
corresponding file in docs/ and let this script (run by
.github/workflows/wiki-sync.yml on every push to main) republish it.

Usage:
    python3 scripts/sync_wiki.py                  # push to the real wiki
    python3 scripts/sync_wiki.py --dry-run OUTDIR  # write the transformed
                                                    # tree to OUTDIR instead
                                                    # of touching any git
                                                    # remote, for local
                                                    # testing of the
                                                    # transform logic
    python3 scripts/sync_wiki.py --remote URL      # override the wiki
                                                    # remote (e.g. a local
                                                    # scratch repo path)
"""
from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DOCS = REPO_ROOT / "docs"
REPO_SLUG = "niels-emmer/myace"

# Source path (relative to docs/) -> Wiki page name (no .md extension).
# Anything under docs/ not listed here (docs/plans/, docs/plan-*.md,
# docs/adr/template.md) is intentionally left out of the Wiki — see
# docs/plans/wiki-docs-sync.md for the reasoning.
PAGE_MAP: dict[str, str] = {
    "README.md": "Home",
    "architecture.md": "Architecture",
    "data-model.md": "Data-Model",
    "invariants.md": "Invariants",
    "extending.md": "Extending-MyACE",
    "debugging.md": "Debugging",
    "ADAPTERS_RESEARCH.md": "Adapter-Research",
    "adr/README.md": "ADR-Index",
}


def adr_page_map() -> dict[str, str]:
    pages: dict[str, str] = {}
    for f in sorted((DOCS / "adr").glob("[0-9]*.md")):
        pages[f"adr/{f.name}"] = f"ADR-{f.stem}"
    return pages


def full_page_map() -> dict[str, str]:
    m = dict(PAGE_MAP)
    m.update(adr_page_map())
    return m


LINK_RE = re.compile(r"(?<!!)\[([^\]]*)\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)")
IMAGE_RE = re.compile(r"!\[([^\]]*)\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)")


def _rewrite_target(target: str, source_rel: str, page_map: dict[str, str]) -> str:
    """Resolve one link/image target found inside docs/<source_rel>."""
    if re.match(r"^[a-zA-Z][a-zA-Z0-9+.-]*://", target) or target.startswith("mailto:"):
        return target  # external link, leave untouched

    frag = ""
    path_part = target
    if "#" in target:
        path_part, frag = target.split("#", 1)
        frag = "#" + frag

    if path_part == "":
        return target  # pure same-page fragment link

    stripped = path_part.rstrip("/")
    source_dir = Path(source_rel).parent  # relative to docs/
    docs_rel = os.path.normpath(str(source_dir / stripped)).replace(os.sep, "/")

    if docs_rel in page_map:
        return f"{page_map[docs_rel]}{frag}"

    # A link to a directory (e.g. "adr/") means its README.md.
    if f"{docs_rel}/README.md" in page_map:
        return f"{page_map[f'{docs_rel}/README.md']}{frag}"

    if docs_rel == "images" or docs_rel.startswith("images/"):
        return f"{docs_rel}{frag}"

    # Anything not published to the Wiki — docs/plans/*, docs/adr/template.md,
    # or something outside docs/ entirely (../README.md, ../AGENTS.md) —
    # points back at the real file in the repo instead of a dead link.
    repo_rel = os.path.normpath(str(Path("docs") / source_dir / stripped)).replace(os.sep, "/")
    return f"https://github.com/{REPO_SLUG}/blob/main/{repo_rel}{frag}"


def transform_content(text: str, source_rel: str, page_map: dict[str, str]) -> str:
    def repl_image(m: re.Match[str]) -> str:
        alt, target = m.group(1), m.group(2)
        return f"![{alt}]({_rewrite_target(target, source_rel, page_map)})"

    def repl_link(m: re.Match[str]) -> str:
        text_, target = m.group(1), m.group(2)
        return f"[{text_}]({_rewrite_target(target, source_rel, page_map)})"

    text = IMAGE_RE.sub(repl_image, text)
    text = LINK_RE.sub(repl_link, text)
    return text


HOME_PREAMBLE = """> Auto-generated from [`docs/`](https://github.com/{slug}/tree/main/docs)
> on every merge to `main`. **Do not edit this Wiki directly** — edits will
> be overwritten. Change the source file in `docs/` and open a PR instead;
> see [`AGENTS.md`](https://github.com/{slug}/blob/main/AGENTS.md#14-documentation-maintenance).

""".format(slug=REPO_SLUG)


def build_sidebar(page_map: dict[str, str]) -> str:
    adr_pages = sorted(adr_page_map().values())
    lines = [
        "### MyACE Docs",
        "",
        "- [Home](Home)",
        "- [Architecture](Architecture)",
        "- [Data Model](Data-Model)",
        "- [Invariants](Invariants)",
        "- [Extending MyACE](Extending-MyACE)",
        "- [Debugging](Debugging)",
        "- [ADR Index](ADR-Index)",
    ]
    for p in adr_pages:
        lines.append(f"  - [{p}]({p})")
    lines.append("- [Adapter Research](Adapter-Research)")
    return "\n".join(lines) + "\n"


def build_footer() -> str:
    return (
        f"---\n\n"
        f"Generated from [`docs/`]({f'https://github.com/{REPO_SLUG}/tree/main/docs'}) "
        f"by [`scripts/sync_wiki.py`]({f'https://github.com/{REPO_SLUG}/blob/main/scripts/sync_wiki.py'}). "
        f"[Back to repo](https://github.com/{REPO_SLUG})\n"
    )


def render_tree(out_dir: Path) -> None:
    page_map = full_page_map()
    out_dir.mkdir(parents=True, exist_ok=True)

    for source_rel, page_name in page_map.items():
        src = DOCS / source_rel
        text = src.read_text()
        text = transform_content(text, source_rel, page_map)
        if source_rel == "README.md":
            text = HOME_PREAMBLE + text
        (out_dir / f"{page_name}.md").write_text(text)

    images_src = DOCS / "images"
    if images_src.is_dir():
        images_dst = out_dir / "images"
        if images_dst.exists():
            shutil.rmtree(images_dst)
        shutil.copytree(images_src, images_dst)

    (out_dir / "_Sidebar.md").write_text(build_sidebar(page_map))
    (out_dir / "_Footer.md").write_text(build_footer())


def run(cmd: list[str], cwd: Path) -> None:
    subprocess.run(cmd, cwd=cwd, check=True)


def sync_to_remote(remote: str, work_dir: Path) -> None:
    if work_dir.exists():
        shutil.rmtree(work_dir)
    work_dir.mkdir(parents=True)

    # Wikis always live on `master`, and a freshly-created wiki repo's
    # remote HEAD symref can point at a branch that doesn't actually exist
    # (e.g. "main") — relying on `git clone`'s implicit checkout to land on
    # the right branch is not reliable. Init + fetch + explicit checkout of
    # `origin/master` by name sidesteps that entirely; if `origin/master`
    # doesn't exist yet (brand new wiki), `cloned` stays False and we just
    # start from an empty tree — the first push creates the repo.
    run(["git", "init"], cwd=work_dir)
    run(["git", "remote", "add", "origin", remote], cwd=work_dir)
    fetch = subprocess.run(["git", "fetch", "origin"], cwd=work_dir)
    cloned = False
    if fetch.returncode == 0:
        checkout = subprocess.run(
            ["git", "checkout", "-B", "master", "origin/master"], cwd=work_dir
        )
        cloned = checkout.returncode == 0

    for item in work_dir.iterdir():
        if item.name == ".git":
            continue
        if item.is_dir():
            shutil.rmtree(item)
        else:
            item.unlink()

    render_tree(work_dir)

    run(["git", "add", "-A"], cwd=work_dir)
    diff = subprocess.run(["git", "diff", "--cached", "--quiet"], cwd=work_dir)
    if diff.returncode == 0 and cloned:
        print("No changes to sync.")
        return

    sha = os.environ.get("GITHUB_SHA", "local")
    run(["git", "config", "user.name", "github-actions[bot]"], cwd=work_dir)
    run(
        ["git", "config", "user.email", "github-actions[bot]@users.noreply.github.com"],
        cwd=work_dir,
    )
    run(["git", "commit", "-m", f"sync from {sha}"], cwd=work_dir)
    run(["git", "push", "origin", "HEAD:master"], cwd=work_dir)
    print("Wiki synced.")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dry-run",
        metavar="OUTDIR",
        help="write the transformed tree to OUTDIR instead of pushing to git",
    )
    parser.add_argument(
        "--remote",
        help="override the wiki git remote (defaults to the real wiki, "
        "using GITHUB_TOKEN if set)",
    )
    args = parser.parse_args()

    if args.dry_run:
        render_tree(Path(args.dry_run))
        print(f"Wrote transformed docs to {args.dry_run}")
        return 0

    remote = args.remote
    if remote is None:
        token = os.environ.get("GITHUB_TOKEN")
        if token:
            remote = f"https://x-access-token:{token}@github.com/{REPO_SLUG}.wiki.git"
        else:
            remote = f"https://github.com/{REPO_SLUG}.wiki.git"

    work_dir = Path(os.environ.get("RUNNER_TEMP", "/tmp")) / "myace-wiki-sync"
    sync_to_remote(remote, work_dir)
    return 0


if __name__ == "__main__":
    sys.exit(main())
