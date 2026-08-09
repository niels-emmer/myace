"""Export canonical artifacts to a GitHub repository as a branch + pull request.

Uses the GitHub REST API directly (no local git clone) — a single tree-based
commit is built from blobs, then a PR is opened from a new branch. Requires a
token with `repo` scope; the token is used for one request and never persisted.
"""

import re

import httpx
import yaml

from app.models.artifact import CanonicalArtifact

GITHUB_API = "https://api.github.com"


class GitHubExportError(Exception):
    """Raised when parsing input or a GitHub API call fails during export."""


def parse_repo(repo: str) -> tuple[str, str]:
    """Parse 'owner/repo' out of a shorthand, HTTPS, or SSH GitHub repo reference."""
    value = repo.strip()
    value = re.sub(r"^git@github\.com:", "", value)
    value = re.sub(r"^https?://github\.com/", "", value)
    value = value.removesuffix(".git").strip("/")
    parts = value.split("/")
    if len(parts) != 2 or not all(parts):
        raise GitHubExportError(f"Could not parse an owner/repo from '{repo}'")
    return parts[0], parts[1]


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", value.strip().lower()).strip("-")
    return slug or "collection"


def _frontmatter(artifact: CanonicalArtifact) -> str:
    fm = {
        "type": artifact.artifact_type,
        "name": artifact.name,
        "version": artifact.version,
        "target_compatibility": artifact.target_compatibility,
        "priority": artifact.priority,
        "tags": artifact.tags,
        "description": artifact.description,
    }
    return yaml.safe_dump(fm, sort_keys=False).strip()


def artifacts_to_files(artifacts: list[CanonicalArtifact]) -> dict[str, str]:
    """Convert canonical artifacts back into the source file-tree layout the
    scanner reads (skills/<name>/SKILL.md, agents/<name>.md, commands/<name>.md,
    a merged AGENTS.md for rules). model_config artifacts are not round-trippable
    into a single file and are skipped — callers should surface that count.
    """
    files: dict[str, str] = {}
    rule_sections: list[str] = []

    for artifact in artifacts:
        safe_name = slugify(artifact.name)
        if artifact.artifact_type == "skill":
            path = f"skills/{safe_name}/SKILL.md"
        elif artifact.artifact_type == "agent":
            path = f"agents/{safe_name}.md"
        elif artifact.artifact_type == "workflow":
            path = f"commands/{safe_name}.md"
        elif artifact.artifact_type == "rule":
            rule_sections.append(f"## {artifact.name}\n\n{artifact.body}".strip())
            continue
        else:
            continue  # model_config — skipped, not a single-file round trip

        files[path] = f"---\n{_frontmatter(artifact)}\n---\n\n{artifact.body}\n"

    if rule_sections:
        files["AGENTS.md"] = "\n\n".join(rule_sections) + "\n"

    return files


async def _gh_request(
    client: httpx.AsyncClient, method: str, path: str, token: str, **kwargs
) -> dict:
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    resp = await client.request(method, f"{GITHUB_API}{path}", headers=headers, **kwargs)
    if resp.status_code >= 400:
        try:
            detail = resp.json().get("message", resp.text)
        except ValueError:
            detail = resp.text
        raise GitHubExportError(f"GitHub API error ({resp.status_code}): {detail}")
    return resp.json() if resp.content else {}


async def export_collection_to_github(
    owner: str,
    repo: str,
    base_branch: str,
    new_branch: str,
    files: dict[str, str],
    commit_message: str,
    pr_title: str,
    pr_body: str,
    token: str,
) -> dict:
    """Branch off base_branch, commit files as one tree-based commit, and open a PR."""
    if not files:
        raise GitHubExportError("Nothing to export — the collection has no exportable artifacts.")

    async with httpx.AsyncClient(timeout=30.0) as client:
        base_ref = await _gh_request(
            client, "GET", f"/repos/{owner}/{repo}/git/ref/heads/{base_branch}", token
        )
        base_sha = base_ref["object"]["sha"]

        base_commit = await _gh_request(
            client, "GET", f"/repos/{owner}/{repo}/git/commits/{base_sha}", token
        )
        base_tree_sha = base_commit["tree"]["sha"]

        tree_entries = []
        for path, content in files.items():
            blob = await _gh_request(
                client, "POST", f"/repos/{owner}/{repo}/git/blobs", token,
                json={"content": content, "encoding": "utf-8"},
            )
            tree_entries.append({
                "path": path,
                "mode": "100644",
                "type": "blob",
                "sha": blob["sha"],
            })

        new_tree = await _gh_request(
            client, "POST", f"/repos/{owner}/{repo}/git/trees", token,
            json={"base_tree": base_tree_sha, "tree": tree_entries},
        )

        new_commit = await _gh_request(
            client, "POST", f"/repos/{owner}/{repo}/git/commits", token,
            json={"message": commit_message, "tree": new_tree["sha"], "parents": [base_sha]},
        )

        await _gh_request(
            client, "POST", f"/repos/{owner}/{repo}/git/refs", token,
            json={"ref": f"refs/heads/{new_branch}", "sha": new_commit["sha"]},
        )

        pr = await _gh_request(
            client, "POST", f"/repos/{owner}/{repo}/pulls", token,
            json={"title": pr_title, "body": pr_body, "head": new_branch, "base": base_branch},
        )

    return {
        "pr_url": pr["html_url"],
        "pr_number": pr["number"],
        "branch": new_branch,
    }
