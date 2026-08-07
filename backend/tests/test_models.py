"""Tests for SQLModel schemas."""

import uuid
from datetime import datetime, timezone
from app.models.user import User, UserCreate, UserRead
from app.models.collection import Collection, CollectionCreate, CollectionRead
from app.models.artifact import Artifact, ArtifactCreate, ArtifactRead, CanonicalArtifact
from app.models.profile import Profile, ProfileCreate, ProfileRead, ProfileCompileRequest
from app.models.token import ApiToken, ApiTokenCreate, ApiTokenRead
from app.models.doc_cache import DocCacheEntry, DocCacheCreate


class TestUserModel:
    """Test User model and schemas."""

    def test_user_create_schema(self):
        """UserCreate should accept valid fields."""
        data = UserCreate(
            email="test@example.com",
            display_name="Test User",
            oidc_sub="sub123",
            oidc_provider="github",
        )
        assert data.email == "test@example.com"
        assert data.display_name == "Test User"

    def test_user_read_schema(self):
        """UserRead should include id and timestamps."""
        now = datetime.now(timezone.utc)
        data = UserRead(
            id=uuid.uuid4(),
            email="test@example.com",
            display_name="Test",
            is_active=True,
            created_at=now,
        )
        assert isinstance(data.id, uuid.UUID)
        assert data.is_active is True


class TestCanonicalArtifact:
    """Test the Canonical IR schema."""

    def test_canonical_artifact_creation(self):
        """CanonicalArtifact should accept all fields."""
        artifact = CanonicalArtifact(
            artifact_type="rule",
            name="test-rule",
            version="1.0.0",
            target_compatibility=["opencode", "claude-code"],
            priority=75,
            tags=["python", "typing"],
            description="Enforce type annotations",
            body="All functions must have type annotations.",
        )
        assert artifact.artifact_type == "rule"
        assert artifact.priority == 75
        assert "opencode" in artifact.target_compatibility

    def test_canonical_artifact_defaults(self):
        """Optional fields should have sensible defaults."""
        artifact = CanonicalArtifact(
            artifact_type="skill",
            name="test",
            version="1.0.0",
            target_compatibility=[],
            priority=50,
            tags=[],
            description="",
            body="content",
        )
        assert artifact.priority == 50
        assert artifact.tags == []


class TestProfileCompileRequest:
    """Test profile compilation request schema."""

    def test_compile_request(self):
        """ProfileCompileRequest should accept valid fields."""
        req = ProfileCompileRequest(
            profile_id=uuid.uuid4(),
            target="opencode",
        )
        assert req.target == "opencode"
        assert req.include_disabled is False

    def test_compile_request_with_include_disabled(self):
        """Should support include_disabled flag."""
        req = ProfileCompileRequest(
            profile_id=uuid.uuid4(),
            target="claude-code",
            include_disabled=True,
        )
        assert req.include_disabled is True
