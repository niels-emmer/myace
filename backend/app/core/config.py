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

    # Doc Cache
    doc_cache_ttl_days: int = 7
    doc_cache_refresh_interval_hours: int = 168

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
