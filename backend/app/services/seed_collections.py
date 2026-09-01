"""Seed the database with starter Collections/Artifacts shipped in the repo's collections/ dir.

collections/base/<slug>/ and collections/additional/<slug>/ hold hand-authored
example content in the same on-disk shape the scanner already reads (skills/,
agents/, commands/, AGENTS.md) and reuses its exact per-file parsers — see
_scan_starter_collection() below for why this doesn't go through
scanner.scan_directory() itself. This module walks those directories and
turns them into Collection/Artifact rows, owned by a dedicated system
account, on every backend startup. It's idempotent: each collection is
looked up by name before insertion, so repeated boots/restarts and
multi-replica startups never create duplicates.
"""

import json
import logging
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.core.config import settings
from app.models.artifact import Artifact
from app.models.collection import Collection
from app.models.user import User
from app.services.scanner import (
    _parse_agent_file,
    _parse_agents_md,
    _parse_command_file,
    _parse_opencode_json,
    _parse_skill_file,
)

logger = logging.getLogger("myace")

SYSTEM_USER_EMAIL = "starter-packs@myace.local"
SYSTEM_USER_DISPLAY_NAME = "MyACE Starter Packs"

STARTER_COLLECTIONS: dict[str, dict[str, dict[str, str]]] = {
    "base": {
        "vibecoder": {
            "name": "Vibecoder",
            "category": "Base Profiles",
            "description": (
                "For solo or prototype work where speed matters more than process. "
                "Minimal gates, broad tool access, and a ship-then-iterate mindset — "
                "with guardrails on secrets and destructive commands."
            ),
        },
        "software-engineer": {
            "name": "Software Engineer",
            "category": "Base Profiles",
            "description": (
                "For production code that must be tested, reviewed, and documented. "
                "A gated multi-agent pipeline (build, verify, security, review, docs) "
                "plus a file-based memory system to carry context across sessions."
            ),
        },
        "data-scientist": {
            "name": "Data Scientist",
            "category": "Base Profiles",
            "description": (
                "For ML and data work that must be reproducible. Notebook-first "
                "exploration, mandatory experiment tracking, data-validation gates, "
                "and rigorous model evaluation before anything ships."
            ),
        },
        "devops-engineer": {
            "name": "DevOps Engineer",
            "category": "Base Profiles",
            "description": (
                "For infrastructure, CI/CD, and platform work that must be safe and "
                "reproducible. A gated multi-agent pipeline (build, verify, security, "
                "review, docs) specialized for IaC (Terraform/Bicep), DevSecOps, "
                "observability, and incident response."
            ),
        },
    },
    "additional": {
        "frontend": {
            "name": "Frontend Specialist",
            "category": "Frontend",
            "description": (
                "For building and maintaining UI code. Component and accessibility "
                "conventions, plus a rule that nothing is done until it's been "
                "visually verified in the running app."
            ),
        },
        "backend": {
            "name": "Backend Specialist",
            "category": "Backend",
            "description": (
                "For service and API code. Clean API design, reversible database "
                "migrations, and test coverage that actually guards the behavior."
            ),
        },
        "iac-expert": {
            "name": "Infrastructure as Code Expert",
            "category": "Infrastructure",
            "description": (
                "For managing infrastructure as code across any cloud. Consistent "
                "naming and invariants, approval-gated applies, documented "
                "exceptions, and review against the well-architected pillars."
            ),
        },
        "azure": {
            "name": "Azure Cloud Architect",
            "category": "Infrastructure",
            "description": (
                "For Azure infrastructure and governance. Well-architected pillars, "
                "landing zones, Entra ID identity, and Azure Policy/Defender security "
                "posture. Layers on the cloud-agnostic iac-expert collection."
            ),
        },
        "aws": {
            "name": "AWS Cloud Architect",
            "category": "Infrastructure",
            "description": (
                "For AWS infrastructure and governance. Well-architected pillars, "
                "landing zones, IAM identity, and Security Hub/GuardDuty/Config "
                "posture. Layers on the cloud-agnostic iac-expert collection."
            ),
        },
        "gcp": {
            "name": "Google Cloud Architect",
            "category": "Infrastructure",
            "description": (
                "For Google Cloud infrastructure and governance. Architecture "
                "Framework pillars, landing zones, IAM/service-account identity, "
                "and Security Command Center posture. Layers on the cloud-agnostic "
                "iac-expert collection."
            ),
        },
        "scaleway": {
            "name": "Scaleway Cloud Architect",
            "category": "Infrastructure",
            "description": (
                "For Scaleway infrastructure and governance. Organization/project "
                "structure, IAM permission scoping, VPC/private-network topology, "
                "security groups, and WAF edge protection. Layers on the "
                "cloud-agnostic iac-expert collection."
            ),
        },
        "auditor": {
            "name": "Security Auditor",
            "category": "Governance & Security",
            "description": (
                "For reviewing code and infrastructure for security issues before "
                "merge. Read-only, checklist-driven review of auth, injection, "
                "secrets, and data handling — grounded in OWASP and NIST."
            ),
        },
        "editor": {
            "name": "Documentation Editor",
            "category": "Documentation",
            "description": (
                "For keeping documentation accurate to the code. Read-only specialist "
                "that updates README, AGENTS/CLAUDE, and inline docs in the same "
                "change set as the code they describe."
            ),
        },
        "fullstack": {
            "name": "Full-Stack Developer",
            "category": "Frontend",
            "description": (
                "For features that span frontend and backend. Contract-first "
                "development, shared type boundaries, and correctness that holds "
                "across the whole stack, not just one layer."
            ),
        },
        "devops": {
            "name": "DevOps / Platform Engineer",
            "category": "Infrastructure",
            "description": (
                "For CI/CD, containers, and platform tooling. Pipeline design, "
                "container builds, observability, incident response, and release "
                "gates that keep deploys safe and repeatable."
            ),
        },
        "java-spring": {
            "name": "Java / Spring Developer",
            "category": "Backend",
            "description": (
                "For Java and Spring Boot services. Layered architecture, dependency "
                "injection discipline, Spring conventions, and reproducible builds."
            ),
        },
        "ios-developer": {
            "name": "iOS Developer",
            "category": "Frontend",
            "description": (
                "For building iOS apps. SwiftUI-first development, state management "
                "patterns, offline-first architecture, and App Store readiness."
            ),
        },
        "android-developer": {
            "name": "Android Developer",
            "category": "Frontend",
            "description": (
                "For building Android apps. Jetpack Compose-first development, state "
                "hoisting, lifecycle-aware architecture, and Play Store readiness."
            ),
        },
        "spec-driven-dev": {
            "name": "Spec-Driven Development",
            "category": "Process & Methodology",
            "description": (
                "For underspecified feature requests that need a written spec before "
                "code. A clarify-plan-analyze workflow with testable acceptance "
                "criteria and a cross-check gate before implementation starts."
            ),
        },
        "ai-engineering": {
            "name": "AI / LLM Engineering",
            "category": "AI/LLM Engineering",
            "description": (
                "For building features around LLMs. Prompt iteration backed by evals, "
                "treating model output as untrusted input, and deliberate "
                "context-window curation — grounded in the 12-factor-agents principles."
            ),
        },
        "eu-ai-act": {
            "name": "EU AI Act Compliance",
            "category": "Governance & Security",
            "description": (
                "For assessing AI systems against the EU AI Act (Regulation "
                "2024/1689). Risk-tier classification, high-risk/transparency/GPAI "
                "obligation reviews, and compliance documentation drafts."
            ),
        },
        "database": {
            "name": "Database Specialist",
            "category": "Backend",
            "description": (
                "For schema, migration, and query work that must stay correct and "
                "fast as data grows. Constraint-driven schema design, safe "
                "migrations, index discipline, and explicit data-integrity decisions."
            ),
        },
        "qa-testing": {
            "name": "QA / Test Engineer",
            "category": "Process & Methodology",
            "description": (
                "For keeping the test suite a real safety net. Test strategy at the "
                "right level, failure-mode coverage, deterministic automation, and "
                "a regression test with every bug fix."
            ),
        },
    },
}


def _scan_starter_collection(collection_dir: Path) -> list[dict]:
    """Parse one starter-collection directory into canonical artifact dicts.

    Mirrors scanner.scan_directory()'s skills/agents/commands/AGENTS.md walk
    and reuses its exact per-file parsers, but skips scanner._resolve_path()'s
    scan_root confinement — that check exists to sandbox arbitrary,
    user-supplied paths from the local-machine-scan API route. collection_dir
    here is always one of our own hardcoded STARTER_COLLECTIONS entries, never
    derived from user input, so that confinement doesn't apply.
    """
    artifacts: list[dict] = []

    skills_dir = collection_dir / "skills"
    if skills_dir.is_dir():
        for skill_dir in sorted(skills_dir.iterdir()):
            if skill_dir.is_dir():
                skill_file = skill_dir / "SKILL.md"
                if skill_file.exists():
                    artifact = _parse_skill_file(skill_file)
                    if artifact:
                        artifacts.append(artifact)

    agents_dir = collection_dir / "agents"
    if agents_dir.is_dir():
        for agent_file in sorted(agents_dir.glob("*.md")):
            artifact = _parse_agent_file(agent_file)
            if artifact:
                artifacts.append(artifact)

    commands_dir = collection_dir / "commands"
    if commands_dir.is_dir():
        for cmd_file in sorted(commands_dir.glob("*.md")):
            artifact = _parse_command_file(cmd_file)
            if artifact:
                artifacts.append(artifact)

    agents_md = collection_dir / "AGENTS.md"
    if agents_md.exists():
        artifacts.extend(_parse_agents_md(agents_md))

    opencode_json = collection_dir / "opencode.json"
    if opencode_json.exists():
        artifacts.extend(_parse_opencode_json(opencode_json))

    return artifacts


async def get_or_create_system_user(session: AsyncSession) -> User:
    """Idempotently fetch (or create) the owner account for starter-pack content.

    password_hash stays None so this account can never authenticate via
    /auth/login, which requires a hash to verify against — it exists purely
    to satisfy Collection.owner_id's NOT NULL foreign key.
    """
    result = await session.execute(select(User).where(User.email == SYSTEM_USER_EMAIL))
    user = result.scalar_one_or_none()
    if user is not None:
        return user

    user = User(
        email=SYSTEM_USER_EMAIL,
        display_name=SYSTEM_USER_DISPLAY_NAME,
        password_hash=None,
        is_active=True,
        is_admin=False,
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user


async def seed_starter_collections(session: AsyncSession) -> None:
    """Idempotently seed starter Collections/Artifacts from collections/{base,additional}/.

    Safe to call on every backend startup — each collection is matched by
    name + is_starter_pack before insertion, so nothing is ever duplicated.
    """
    collections_root = Path(settings.collections_root)
    if not collections_root.is_dir():
        # Not a misconfiguration — e.g. the backend running outside Docker
        # without COLLECTIONS_ROOT set. No starter packs, nothing else changes.
        logger.info(
            "Starter collections directory not found at %s — skipping seed.", collections_root
        )
        return

    system_user: User | None = None

    for collection_type, collections in STARTER_COLLECTIONS.items():
        type_dir = collections_root / collection_type
        for slug, meta in collections.items():
            collection_dir = type_dir / slug
            if not collection_dir.is_dir():
                logger.warning(
                    "Starter collection directory missing: %s — skipping.", collection_dir
                )
                continue

            existing = await session.execute(
                select(Collection).where(
                    Collection.name == meta["name"],
                    Collection.is_starter_pack.is_(True),
                )
            )
            if existing.scalar_one_or_none() is not None:
                continue

            if system_user is None:
                system_user = await get_or_create_system_user(session)

            scanned = _scan_starter_collection(collection_dir)

            collection = Collection(
                owner_id=system_user.id,
                name=meta["name"],
                description=meta["description"],
                git_url=f"seed://{collection_type}/{slug}",
                collection_type=collection_type,
                visibility="public",
                published=True,
                moderation_status="approved",
                category=meta["category"],
                is_starter_pack=True,
                artifact_count=len(scanned),
            )
            session.add(collection)
            await session.commit()
            await session.refresh(collection)

            for item in scanned:
                session.add(
                    Artifact(
                        collection_id=collection.id,
                        artifact_type=item["artifact_type"],
                        name=item["name"],
                        version=item.get("version", "1.0.0"),
                        priority=item.get("priority", 50),
                        target_compatibility=json.dumps(item.get("target_compatibility", [])),
                        tags=json.dumps(item.get("tags", [])),
                        description=item.get("description", ""),
                        body=item.get("body", ""),
                        file_path=item.get("file_path", ""),
                        handoff_to=(
                            json.dumps(item["handoff_to"])
                            if item.get("handoff_to") is not None
                            else None
                        ),
                    )
                )

            await session.commit()
            logger.info(
                "Seeded starter collection %r (%s) with %d artifacts.",
                meta["name"], collection_type, len(scanned),
            )
