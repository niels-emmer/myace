"""Local environment scanner — discovers and converts local configs to Canonical IR."""

import json
import re
from pathlib import Path

import yaml


def scan_directory(path: str | Path) -> list[dict]:
    """
    Scan a local config directory and return a list of canonical artifacts.

    Handles:
      - skills/<name>/SKILL.md        → skill artifacts
      - agents/<name>.md              → agent artifacts
      - commands/<name>.md            → workflow artifacts
      - AGENTS.md                     → rule artifacts (## sections)
      - opencode.json                 → model_config artifacts
    """
    base = Path(path).expanduser()
    if not base.exists():
        # Try resolving symlinks manually
        try:
            resolved = base.resolve(strict=False)
            if resolved.exists():
                base = resolved
        except (OSError, RuntimeError):
            pass
    if not base.exists():
        raise FileNotFoundError(f"Directory not found: {base}")

    artifacts: list[dict] = []

    # 1. Scan skills/
    skills_dir = base / "skills"
    if skills_dir.is_dir():
        for skill_dir in sorted(skills_dir.iterdir()):
            if skill_dir.is_dir():
                skill_file = skill_dir / "SKILL.md"
                if skill_file.exists():
                    artifact = _parse_skill_file(skill_file)
                    if artifact:
                        artifacts.append(artifact)

    # 2. Scan agents/
    agents_dir = base / "agents"
    if agents_dir.is_dir():
        for agent_file in sorted(agents_dir.glob("*.md")):
            artifact = _parse_agent_file(agent_file)
            if artifact:
                artifacts.append(artifact)

    # 3. Scan commands/ (as workflows)
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


def _parse_yaml_frontmatter(content: str) -> tuple[dict, str]:
    """Extract YAML frontmatter and body from a markdown file."""
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
    """Parse a SKILL.md file into a canonical artifact."""
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
    """Parse an agent .md file into a canonical artifact."""
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
    """Parse a command .md file into a workflow artifact."""
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
    """Parse AGENTS.md into individual rule artifacts (one per ## section)."""
    content = path.read_text(encoding="utf-8")
    artifacts: list[dict] = []

    # Split by ## headers
    sections = re.split(r"\n(?=## )", content)
    for section in sections:
        section = section.strip()
        if not section:
            continue

        # Extract header name
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
    """Parse opencode.json for model configs and MCP server definitions."""
    artifacts: list[dict] = []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return artifacts

    # Extract model configs
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

    # Extract MCP server configs
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


def export_to_collection(
    artifacts: list[dict],
    output_dir: str | Path,
    collection_name: str = "imported-config",
) -> Path:
    """
    Write canonical artifacts as Markdown files with YAML frontmatter
    into a directory ready for Git.
    """
    output = Path(output_dir).expanduser().resolve()
    output.mkdir(parents=True, exist_ok=True)

    for artifact in artifacts:
        atype = artifact["artifact_type"]
        name = artifact["name"]
        safe_name = re.sub(r"[^a-zA-Z0-9_-]", "_", name)

        # Determine subdirectory
        type_dir = {
            "rule": "rules",
            "skill": "skills",
            "agent": "agents",
            "workflow": "workflows",
            "model_config": "configs",
        }.get(atype, "other")

        file_dir = output / type_dir
        file_dir.mkdir(parents=True, exist_ok=True)
        file_path = file_dir / f"{safe_name}.md"

        # Build frontmatter
        frontmatter = {
            "type": atype,
            "name": name,
            "version": artifact.get("version", "1.0.0"),
            "target_compatibility": artifact.get("target_compatibility", []),
            "priority": artifact.get("priority", 50),
            "tags": artifact.get("tags", []),
            "description": artifact.get("description", ""),
        }

        frontmatter_yaml = yaml.dump(frontmatter, default_flow_style=False, sort_keys=False)
        file_content = f"---\n{frontmatter_yaml}---\n\n{artifact['body']}\n"
        file_path.write_text(file_content, encoding="utf-8")

    # Write a README
    readme = output / "README.md"
    readme.write_text(
        f"# {collection_name}\n\n"
        f"Imported {len(artifacts)} artifacts from local environment.\n\n"
        f"## Contents\n\n"
        f"| Type | Count |\n"
        f"|------|-------|\n"
    )
    for atype in ["rule", "skill", "agent", "workflow", "model_config"]:
        count = sum(1 for a in artifacts if a["artifact_type"] == atype)
        if count:
            with open(readme, "a") as f:
                f.write(f"| {atype}s | {count} |\n")

    return output
