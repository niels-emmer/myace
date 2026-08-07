"""CLI-side Cursor adapter."""

from myace_cli.adapters.base import BaseAdapter


class CursorAdapter(BaseAdapter):
    """CLI-side adapter for Cursor — generates .cursorrules and .mdc files."""

    def adapter_name(self) -> str:
        return "cursor"

    def supported_targets(self) -> list[str]:
        return ["cursor", "cursor-editor"]

    def translate(self, artifacts: list[dict]) -> dict[str, str]:
        files: dict[str, str] = {}
        rules: list[str] = []
        idx = 0

        for artifact in artifacts:
            atype = artifact.get("artifact_type", "rule")
            name = artifact.get("name", "unnamed")
            body = artifact.get("body", "")
            desc = artifact.get("description", "")
            priority = artifact.get("priority", 50)

            if atype == "rule":
                rules.append(f"- **{name}** (priority {priority}): {desc}\n  {body}\n")
            elif atype in ("skill", "agent"):
                files[f".cursor/rules/rule_{idx:03d}.mdc"] = (
                    f"---\ntitle: {name}\ndescription: {desc}\ntype: {atype}\npriority: {priority}\n---\n{body}\n"
                )
                idx += 1
            elif atype == "workflow":
                files[f".cursor/workflows/{name}.mdc"] = (
                    f"---\ntitle: {name}\ndescription: {desc}\ntype: workflow\n---\n{body}\n"
                )

        if rules:
            files[".cursorrules"] = "# Cursor Rules\n\n" + "\n".join(rules)

        return files
