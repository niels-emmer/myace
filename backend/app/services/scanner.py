"""Backend scanner — mirrors the CLI scanner for server-side directory scanning."""

import json
import re
import shutil
import tempfile
from pathlib import Path
from urllib.parse import urlparse

import git
import yaml

from app.core.config import settings


def _redact_credentials(url: str) -> str:
    """Remove embedded credentials from a URL for safe logging/error messages."""
    parsed = urlparse(url)
    if parsed.username or parsed.password:
        # Reconstruct without credentials
        netloc = parsed.hostname or ""
        if parsed.port:
            netloc = f"{netloc}:{parsed.port}"
        return parsed._replace(netloc=netloc).geturl()
    return url


def _resolve_path(path: str) -> Path:
    """Resolve a user-supplied path, handling Docker mount and broken symlinks.

    The resolved path MUST be under the configured scan_root (settings.scan_root)
    to prevent arbitrary file reads. In Docker, scan_root defaults to /host-home.
    """
    base = Path(path).expanduser()

    # If it exists directly, use it
    if base.exists():
        resolved = base
    # If it's a broken symlink, try to resolve the target through Docker mounts
    elif base.is_symlink():
        target = Path(base.readlink())
        if target.is_absolute():
            # Try rewriting the absolute target path through known mount points
            for mount, host_prefix in [("/host-home", "/Users/nemmer"),
                                        ("/host-home", "/home"),
                                        ("/host", "/Users"),
                                        ("/mnt/host", "/Users")]:
                alt = Path(str(target).replace(host_prefix, mount, 1))
                if alt.exists():
                    resolved = alt
                    break
            else:
                raise FileNotFoundError(f"Directory not found: {base}")
        else:
            raise FileNotFoundError(f"Directory not found: {base}")
    else:
        # Docker workaround: ~ expands to /root/ inside the container.
        # Try rewriting common home prefixes to the mounted host home.
        str_base = str(base)
        for host_prefix, mount in [("/root", "/host-home"),
                                    ("/home", "/host-home"),
                                    ("/Users", "/host-home")]:
            if str_base.startswith(host_prefix):
                alt = Path(str_base.replace(host_prefix, mount, 1))
                if alt.exists():
                    resolved = alt
                    break
                # Also check if the alt is a broken symlink we can resolve
                if alt.is_symlink():
                    target = Path(alt.readlink())
                    for m, hp in [("/host-home", "/Users/nemmer"),
                                  ("/host-home", "/home")]:
                        resolved_alt = Path(str(target).replace(hp, m, 1))
                        if resolved_alt.exists():
                            resolved = resolved_alt
                            break
                    else:
                        continue
                    break
            else:
                continue
            break
        else:
            raise FileNotFoundError(f"Directory not found: {base}")

    # Confine the resolved path to the configured scan root.
    scan_root = Path(settings.scan_root).resolve()
    try:
        resolved.relative_to(scan_root)
    except ValueError:
        raise PermissionError(
            f"Path '{resolved}' is outside the allowed scan root '{scan_root}'"
        )

    return resolved


def scan_directory(path: str | Path) -> list[dict]:
    """Scan a local config directory and return canonical artifacts."""
    base = _resolve_path(str(path))

    artifacts: list[dict] = []

    # 1. Scan skills/<name>/SKILL.md
    skills_dir = base / "skills"
    if skills_dir.is_dir():
        for skill_dir in sorted(skills_dir.iterdir()):
            if skill_dir.is_dir():
                skill_file = skill_dir / "SKILL.md"
                if skill_file.exists():
                    artifact = _parse_skill_file(skill_file)
                    if artifact:
                        artifacts.append(artifact)

    # 2. Scan agents/<name>.md
    agents_dir = base / "agents"
    if agents_dir.is_dir():
        for agent_file in sorted(agents_dir.glob("*.md")):
            artifact = _parse_agent_file(agent_file)
            if artifact:
                artifacts.append(artifact)

    # 3. Scan commands/<name>.md as workflows
    commands_dir = base / "commands"
    if commands_dir.is_dir():
        for cmd_file in sorted(commands_dir.glob("*.md")):
            artifact = _parse_command_file(cmd_file)
            if artifact:
                artifacts.append(artifact)

    # 4. Parse AGENTS.md for rules
    agents_md = base / "AGENTS.md"
    if agents_md.exists():
        rules = _parse_agents_md(agents_md)
        artifacts.extend(rules)

    # 5. Parse opencode.json for model configs
    opencode_json = base / "opencode.json"
    if opencode_json.exists():
        configs = _parse_opencode_json(opencode_json)
        artifacts.extend(configs)

    return artifacts


def _validate_git_url(url: str) -> str:
    """Validate a git URL and strip embedded credentials.

    Only https:// and git:// schemes are allowed. Credentials are stripped
    from the returned URL to prevent credential leakage in error messages.
    Raises ValueError if the URL is invalid or uses a disallowed scheme.
    """
    parsed = urlparse(url)
    if parsed.scheme not in ("https", "git"):
        raise ValueError(
            f"Disallowed git URL scheme '{parsed.scheme}'. Only https:// and git:// are permitted."
        )
    # Strip credentials for safe use
    safe_url = _redact_credentials(url)
    return safe_url


def scan_git_repository(
    repo_url: str,
    branch: str = "main",
    subdirectory: str = "",
) -> list[dict]:
    """Shallow-clone a Git repository into a temp dir and scan it for canonical artifacts.

    Only public repositories work out of the box. For private repos, use a
    deploy token or SSH key configured on the server — do not embed credentials
    in the URL, as they may leak in error messages.
    """
    # Validate and sanitize the URL before any operation
    safe_url = _validate_git_url(repo_url)

    tmp_dir = tempfile.mkdtemp(prefix="myace-scan-")
    try:
        try:
            git.Repo.clone_from(repo_url, tmp_dir, branch=branch, depth=1, single_branch=True)
        except git.exc.GitCommandError as e:
            raise ValueError(f"Failed to clone repository (branch '{branch}'): {e}") from e

        scan_root = Path(tmp_dir)
        if subdirectory:
            scan_root = scan_root / subdirectory
            if not scan_root.is_dir():
                raise FileNotFoundError(f"Subdirectory '{subdirectory}' not found in repository")

        return scan_directory(scan_root)
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


def _parse_yaml_frontmatter(content: str) -> tuple[dict, str]:
    """Extract YAML frontmatter and body from markdown."""
    match = re.match(r"^---\n(.*?)\n---\n(.*)", content, re.DOTALL)
    if match:
        try:
            frontmatter = yaml.safe_load(match.group(1)) or {}
        except yaml.YAMLError:
            frontmatter = {}
        body = match.group(2).strip()
        return frontmatter, body
    return {}, content.strip()


def _parse_skill_file(path: Path) -> dict | None:
    content = path.read_text(encoding="utf-8")
    frontmatter, body = _parse_yaml_frontmatter(content)
    name = frontmatter.get("name", path.parent.name)
    compatibility = frontmatter.get("compatibility", "opencode")
    if isinstance(compatibility, str):
        compatibility = [compatibility]
    return {
        "artifact_type": "skill",
        "name": name,
        "version": frontmatter.get("version", "1.0.0"),
        "priority": frontmatter.get("priority", 50),
        "target_compatibility": compatibility,
        "tags": frontmatter.get("tags", []),
        "description": frontmatter.get("description", ""),
        "body": body,
        "file_path": str(path.relative_to(path.parents[2]) if len(path.parents) > 2 else path.name),
    }


def _parse_agent_file(path: Path) -> dict | None:
    content = path.read_text(encoding="utf-8")
    frontmatter, body = _parse_yaml_frontmatter(content)
    name = path.stem
    tags = []
    if frontmatter.get("mode"):
        tags.append(f"mode:{frontmatter['mode']}")
    if frontmatter.get("model"):
        tags.append(f"model:{frontmatter['model']}")
    return {
        "artifact_type": "agent",
        "name": name,
        "version": frontmatter.get("version", "1.0.0"),
        "priority": frontmatter.get("priority", 50),
        "target_compatibility": frontmatter.get("compatibility", ["opencode"]),
        "tags": tags,
        "description": frontmatter.get("description", ""),
        "body": body,
        "file_path": str(path.relative_to(path.parent) if path.parent else path.name),
    }


def _parse_command_file(path: Path) -> dict | None:
    content = path.read_text(encoding="utf-8")
    frontmatter, body = _parse_yaml_frontmatter(content)
    name = path.stem
    return {
        "artifact_type": "workflow",
        "name": name,
        "version": frontmatter.get("version", "1.0.0"),
        "priority": frontmatter.get("priority", 50),
        "target_compatibility": frontmatter.get("compatibility", ["opencode"]),
        "tags": frontmatter.get("tags", []),
        "description": frontmatter.get("description", ""),
        "body": body,
        "file_path": str(path.relative_to(path.parent) if path.parent else path.name),
    }


def _parse_agents_md(path: Path) -> list[dict]:
    content = path.read_text(encoding="utf-8")
    artifacts = []
    sections = re.split(r"\n(?=## )", content)
    for section in sections:
        section = section.strip()
        if not section:
            continue
        header_match = re.match(r"## (.+)", section)
        if not header_match:
            continue
        name = header_match.group(1).strip()
        body = section[len(header_match.group(0)):].strip()
        artifacts.append({
            "artifact_type": "rule",
            "name": name,
            "version": "1.0.0",
            "priority": 50,
            "target_compatibility": ["opencode"],
            "tags": [],
            "description": f"Rule: {name}",
            "body": body,
            "file_path": "AGENTS.md",
        })
    return artifacts


def _parse_opencode_json(path: Path) -> list[dict]:
    artifacts = []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return artifacts
    provider = data.get("provider", {})
    for provider_name, provider_config in provider.items():
        models = provider_config.get("models", {})
        for model_name, model_config in models.items():
            artifacts.append({
                "artifact_type": "model_config",
                "name": f"model:{model_name}",
                "version": "1.0.0",
                "priority": 50,
                "target_compatibility": ["opencode"],
                "tags": [f"provider:{provider_name}"],
                "description": f"Model config for {model_name} via {provider_name}",
                "body": json.dumps(model_config, indent=2),
                "file_path": "opencode.json",
            })
    mcp = data.get("mcp", {})
    for server_name, server_config in mcp.items():
        artifacts.append({
            "artifact_type": "model_config",
            "name": f"mcp:{server_name}",
            "version": "1.0.0",
            "priority": 50,
            "target_compatibility": ["opencode"],
            "tags": ["mcp"],
            "description": f"MCP server: {server_name}",
            "body": json.dumps(server_config, indent=2),
            "file_path": "opencode.json",
        })
    return artifacts
