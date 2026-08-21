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
                "Fast, pragmatic starting point for solo/prototype work — minimal gates, "
                "permissive tool access, ships-first discipline."
            ),
        },
        "software-engineer": {
            "name": "Software Engineer",
            "category": "Base Profiles",
            "description": (
                "Rigorous, production-grade starting point — gated multi-agent lifecycle, "
                "security/testing/documentation discipline, file-based memory system."
            ),
        },
        "data-scientist": {
            "name": "Data Scientist",
            "category": "Base Profiles",
            "description": (
                "Exploratory, notebook-driven workflow with experiment tracking, "
                "data validation gates, model evaluation discipline, and "
                "reproducible pipelines — built for ML and data work."
            ),
        },
    },
    "additional": {
        "frontend": {
            "name": "Frontend Specialist",
            "category": "Frontend",
            "description": (
                "UI/component conventions, accessibility, and a 'never done until visually "
                "verified' discipline."
            ),
        },
        "backend": {
            "name": "Backend Specialist",
            "category": "Backend",
            "description": (
                "API design, migration discipline, and test-coverage conventions for "
                "service code."
            ),
        },
        "iac-expert": {
            "name": "Infrastructure as Code Expert",
            "category": "Infrastructure",
            "description": (
                "Cloud-agnostic IaC governance — invariants, naming, approval-gated "
                "applies, documented exceptions, well-architected pillar review."
            ),
        },
        "azure": {
            "name": "Azure Cloud Architect",
            "category": "Infrastructure",
            "description": (
                "Azure-specific architecture and governance — WAF pillars, CAF "
                "landing zones, Entra ID identity, Azure Policy/Defender security "
                "posture. Layers on the vendor-agnostic iac-expert collection."
            ),
        },
        "aws": {
            "name": "AWS Cloud Architect",
            "category": "Infrastructure",
            "description": (
                "AWS-specific architecture and governance — WAF pillars, CAF "
                "landing zones, IAM identity, Security Hub/GuardDuty/Config "
                "posture. Layers on the vendor-agnostic iac-expert collection."
            ),
        },
        "gcp": {
            "name": "Google Cloud Architect",
            "category": "Infrastructure",
            "description": (
                "GCP-specific architecture and governance — Architecture "
                "Framework pillars, GCAF landing zones, IAM/service-account "
                "identity, Security Command Center posture. Layers on the "
                "vendor-agnostic iac-expert collection."
            ),
        },
        "auditor": {
            "name": "Security Auditor",
            "category": "Governance & Security",
            "description": (
                "Read-only security/compliance review persona — structured checklists, "
                "threat-modeling, data-classification-aware model routing."
            ),
        },
        "editor": {
            "name": "Documentation Editor",
            "category": "Documentation",
            "description": (
                "Read-only docs/content specialist — keeps README/AGENTS/CLAUDE docs in "
                "sync with code changes."
            ),
        },
        "fullstack": {
            "name": "Full-Stack Developer",
            "category": "Frontend",
            "description": (
                "End-to-end frontend + backend discipline — contract-first "
                "development, shared type boundaries, integration-level "
                "correctness, and error propagation across the stack."
            ),
        },
        "devops": {
            "name": "DevOps / Platform Engineer",
            "category": "Infrastructure",
            "description": (
                "CI/CD pipeline design, container builds, observability stack, "
                "incident response discipline, and release gate automation."
            ),
        },
        "java-spring": {
            "name": "Java / Spring Developer",
            "category": "Backend",
            "description": (
                "Layered architecture, dependency injection discipline, "
                "Spring Boot conventions, and build reproducibility."
            ),
        },
        "ios-developer": {
            "name": "iOS Developer",
            "category": "Frontend",
            "description": (
                "SwiftUI-first development, state management patterns, "
                "App Store readiness, and offline-first architecture."
            ),
        },
        "android-developer": {
            "name": "Android Developer",
            "category": "Frontend",
            "description": (
                "Jetpack Compose-first development, state hoisting, "
                "Play Store readiness, and lifecycle-aware architecture."
            ),
        },
        "spec-driven-dev": {
            "name": "Spec-Driven Development",
            "category": "Process & Methodology",
            "description": (
                "Spec → clarify → plan → tasks → analyze → implement workflow "
                "for underspecified feature requests, adapted from GitHub's "
                "spec-kit — a living project constitution, testable acceptance "
                "criteria, and a cross-check gate before implementation starts."
            ),
        },
        "ai-engineering": {
            "name": "AI / LLM Engineering",
            "category": "AI/LLM Engineering",
            "description": (
                "Prompt iteration backed by evals, LLM-integrated feature "
                "development that treats model output as untrusted input, and "
                "deliberate context-window curation — grounded in the "
                "12-factor-agents principles."
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
