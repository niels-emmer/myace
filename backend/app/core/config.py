"""Application configuration via pydantic-settings."""


from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Application
    app_name: str = "MyACE"
    app_env: str = "development"
    app_secret_key: str = "change-me-to-a-random-64-char-string"
    debug: bool = True

    # Database
    database_url: str = "postgresql+asyncpg://myace:myace_secret@postgres:5432/myace"

    # OIDC
    oidc_client_id: str = ""
    oidc_client_secret: str = ""
    oidc_issuer_url: str = ""
    oidc_scopes: str = "openid profile email"

    # GitHub OAuth
    github_client_id: str = ""
    github_client_secret: str = ""

    # Google OAuth
    google_client_id: str = ""
    google_client_secret: str = ""

    # API Keys
    api_key_length: int = 48

    # Admin bootstrap
    admin_emails: str = ""
    # First-ever registered user becomes admin when this is true (the only
    # way to get an admin on a totally fresh database). Set to false in
    # production once your own admin account exists, so a public multi-tenant
    # deployment doesn't hand admin to whoever registers first after that.
    admin_bootstrap_enabled: bool = True

    # CORS
    cors_origins: str = "https://myace.localhost"

    # Trusted hosts (comma-separated). Empty disables the check — set this to
    # your real domain(s) once DNS is live for a public deployment.
    trusted_hosts: str = ""

    # Scan root — confine local directory scanning to this directory.
    # In Docker (docker-compose.dev.yml), the host home is mounted at /host-home.
    # Set this to the intended scan root for your deployment.
    scan_root: str = "/host-home"

    # Starter-pack collections — read by seed_starter_collections() on boot.
    # docker-compose.yml mounts the repo's collections/ directory at this path
    # inside the backend container. Running the backend outside Docker (e.g.
    # `uvicorn app.main:app` from backend/), set this to the repo-root
    # collections/ directory instead.
    collections_root: str = "/app/collections"

    # Community collections
    community_repo: str = "nemmer/MyACE"

    # Doc Cache
    doc_cache_ttl_days: int = 7
    doc_cache_refresh_interval_hours: int = 168

    # SMTP — used for password-reset emails. All fields are the bootstrap
    # default; a non-empty value saved via the System Settings UI (stored
    # encrypted in system_settings) overrides these at runtime — see
    # app/services/effective_settings.py.
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_username: str = ""
    smtp_password: str = ""
    smtp_from_email: str = ""
    smtp_from_name: str = "MyACE"
    smtp_use_tls: bool = True

    # Security — symmetric key for encrypting admin-editable secrets (SMTP
    # password, OAuth client secrets) stored in the database. Generate with:
    # python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
    settings_encryption_key: str = ""

    # Base URL of the frontend, used to build links in outgoing emails
    # (e.g. the password-reset link). Does not affect API/CORS behavior.
    frontend_base_url: str = "http://localhost:5173"

    # Community collection freshness — how many days a manual
    # last_verified_at is considered current before GET /admin/freshness-queue
    # and app/scripts/check_collection_freshness.py flag it for re-review.
    # Default ~6 months.
    collection_freshness_threshold_days: int = 180

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def oidc_scope_list(self) -> list[str]:
        return [s.strip() for s in self.oidc_scopes.split(" ") if s.strip()]

    @property
    def admin_email_list(self) -> list[str]:
        return [e.strip().lower() for e in self.admin_emails.split(",") if e.strip()]

    @property
    def trusted_host_list(self) -> list[str]:
        return [h.strip() for h in self.trusted_hosts.split(",") if h.strip()]


settings = Settings()
