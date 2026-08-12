"""Symmetric encryption for admin-editable secrets stored in the database.

SMTP passwords and OAuth client secrets entered via the System Settings UI
are encrypted at rest with Fernet (AES-128-CBC + HMAC), keyed by
`settings.settings_encryption_key`. See docs/adr/0006-encrypted-admin-editable-secrets.md.
"""

from cryptography.fernet import Fernet, InvalidToken

from app.core.config import settings


class SettingsEncryptionKeyError(RuntimeError):
    """Raised when an encrypt/decrypt is attempted without a configured key."""


def _get_fernet() -> Fernet:
    if not settings.settings_encryption_key:
        raise SettingsEncryptionKeyError(
            "SETTINGS_ENCRYPTION_KEY is not set. Generate one with: "
            "python -c \"from cryptography.fernet import Fernet; "
            "print(Fernet.generate_key().decode())\" and set it in .env before "
            "saving secrets (SMTP password, OAuth client secrets) via System Settings."
        )
    return Fernet(settings.settings_encryption_key.encode("utf-8"))


def encrypt_secret(plaintext: str) -> str:
    """Encrypt a plaintext secret for storage. Returns a URL-safe base64 token."""
    return _get_fernet().encrypt(plaintext.encode("utf-8")).decode("utf-8")


def decrypt_secret(ciphertext: str) -> str:
    """Decrypt a stored secret. Raises InvalidToken if the key doesn't match."""
    return _get_fernet().decrypt(ciphertext.encode("utf-8")).decode("utf-8")


__all__ = ["SettingsEncryptionKeyError", "InvalidToken", "encrypt_secret", "decrypt_secret"]
