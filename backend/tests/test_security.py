"""Tests for security utilities."""

from app.core.security import generate_api_key, generate_oidc_state, hash_api_key, verify_api_key


class TestApiKey:
    """Test API key generation, hashing, and verification."""

    def test_generate_api_key_length(self):
        """Generated key should match configured length."""
        key = generate_api_key()
        # URL-safe base64 encoded: 48 bytes -> 64 chars
        assert len(key) >= 48

    def test_generate_api_key_unique(self):
        """Each generated key should be unique."""
        keys = {generate_api_key() for _ in range(100)}
        assert len(keys) == 100

    def test_hash_and_verify(self):
        """Hashed key should verify correctly."""
        key = generate_api_key()
        hashed = hash_api_key(key)
        assert verify_api_key(key, hashed)

    def test_wrong_key_fails_verification(self):
        """Wrong key should not verify against a hash."""
        key = generate_api_key()
        hashed = hash_api_key(key)
        assert not verify_api_key("wrong-key", hashed)

    def test_same_key_different_hashes(self):
        """Same key should produce different hashes each time (bcrypt salt)."""
        key = generate_api_key()
        hash1 = hash_api_key(key)
        hash2 = hash_api_key(key)
        assert hash1 != hash2


class TestOidcState:
    """Test OIDC state parameter generation."""

    def test_state_length(self):
        """State should be sufficiently long."""
        state = generate_oidc_state()
        assert len(state) >= 32

    def test_state_unique(self):
        """Each state should be unique."""
        states = {generate_oidc_state() for _ in range(100)}
        assert len(states) == 100
