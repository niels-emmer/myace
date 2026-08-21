// ─── Canonical IR Types ──────────────────────────────────────

export type ArtifactType = 'rule' | 'skill' | 'agent' | 'workflow' | 'model_config';

export interface CanonicalArtifact {
  artifact_type: ArtifactType;
  name: string;
  version: string;
  target_compatibility: string[];
  priority: number;
  tags: string[];
  description: string;
  body: string;
  // Optional pipeline-routing metadata for agent artifacts — the names of
  // agents this one may hand work off to (see docs/adr/0010-structured-handoff-field.md).
  // undefined/absent means "not declared"; distinct from an empty array
  // ("declared, but terminal — never hands off").
  handoff_to?: string[] | null;
  source_collection_id?: string;
  source_collection_name?: string;
}

// ─── Collection Types ────────────────────────────────────────

export type CollectionType = 'base' | 'additional';
export type Visibility = 'private' | 'public';
export type ModerationStatus = 'draft' | 'submitted' | 'approved' | 'denied' | 'unpublished';

export interface Collection {
  id: string;
  owner_id: string;
  name: string;
  description?: string;
  git_url: string;
  git_branch: string;
  collection_type: CollectionType;
  visibility: Visibility;
  is_active: boolean;
  artifact_count: number;
  download_count: number;
  published: boolean;
  category?: string;
  avg_rating: number;
  rating_count: number;
  moderation_status: ModerationStatus;
  moderation_reason?: string;
  submitted_at?: string;
  moderated_at?: string;
  moderated_by?: string;
  last_synced_at?: string;
  // Manual freshness verification (Epic 4.5) — a moderator/admin
  // confirming this collection is still good, not an automated check
  // against live tool documentation. last_verified_at is an ISO date
  // string (YYYY-MM-DD), not a full timestamp.
  last_verified_at?: string | null;
  verified_by?: string | null;
  created_at: string;
  updated_at: string;
}

export interface ModerationQueueItem extends Collection {
  owner_email: string;
  owner_display_name: string;
}

export interface CollectionRatingSummary {
  avg_rating: number;
  rating_count: number;
  my_rating: number | null;
}

export interface CollectionComment {
  id: string;
  collection_id: string;
  user_id: string;
  author_display_name: string;
  body: string;
  created_at: string;
}

export interface CollectionCreate {
  name: string;
  description?: string;
  git_url: string;
  git_branch?: string;
  collection_type?: CollectionType;
  visibility?: Visibility;
  category?: string;
}

export interface CollectionUpdate {
  name?: string;
  description?: string;
  collection_type?: CollectionType;
  visibility?: Visibility;
  category?: string;
}

// ─── Artifact Types ──────────────────────────────────────────

export interface Artifact {
  id: string;
  collection_id: string;
  artifact_type: ArtifactType;
  name: string;
  version: string;
  priority: number;
  target_compatibility: string[];
  tags: string[];
  description?: string;
  body: string;
  file_path: string;
  handoff_to?: string[] | null;
  is_enabled: boolean;
  created_at: string;
  updated_at: string;
}

// ─── Profile Types ───────────────────────────────────────────

export interface Profile {
  id: string;
  owner_id: string;
  name: string;
  description?: string;
  base_collection_id: string;
  additional_collection_ids: string[];
  disabled_artifact_ids: string[];
  target_framework?: string;
  is_public: boolean;
  version: number;
  created_at: string;
  updated_at: string;
}

export interface ProfileCreate {
  name: string;
  description?: string;
  base_collection_id: string;
  additional_collection_ids?: string[];
  disabled_artifact_ids?: string[];
  target_framework?: string;
  is_public?: boolean;
}

export interface ProfileCompileRequest {
  profile_id: string;
  target: string;
  include_disabled?: boolean;
}

export interface ValidationIssue {
  level: 'warning';
  code: string;
  message: string;
}

export interface CompileResult {
  profile_id: string;
  profile_name: string;
  target: string;
  artifact_count: number;
  files: Record<string, string>;
  // Optional — response-only, never persisted (see docs/data-model.md). Advisory
  // problems surfaced at compile time, e.g. an artifact name collision across
  // composed collections; an empty/absent array means nothing to flag.
  warnings?: ValidationIssue[];
  // sha256 over a deterministic serialization of `files` — see
  // backend/app/services/compiler.py's compute_compiled_hash(). What the CLI's
  // sync manifest and GET /profiles/{id}/compile-status compare against to
  // detect server-side staleness (docs/adr/0009-manifest-based-drift-detection.md).
  compiled_hash: string;
}

// Mirrors backend ProfileCompileStatusResponse (GET /profiles/{id}/compile-status).
// No frontend caller today — that endpoint is CLI-only (myace check/watch
// poll it directly) — kept here for schema parity so a future web-UI
// staleness indicator doesn't have to invent this shape from scratch.
export interface CompileStatusResult {
  compiled_hash: string;
  updated_at: string;
}

// ─── Sync Dashboard ──────────────────────────────────────────

export interface SyncStatus {
  id: string;
  profile_id: string;
  profile_name: string;
  target: string;
  machine_label: string;
  in_sync: boolean;
  locally_modified_files: string[];
  last_checked_at: string;
}

// Mirrors backend SyncReportRequest (POST /sync/report). No frontend caller
// today — reporting is CLI-only (`myace check --report`/`watch --report`);
// kept for schema parity, same reasoning as CompileStatusResult above.
export interface SyncReportRequest {
  profile_id: string;
  target: string;
  machine_label: string;
  in_sync: boolean;
  locally_modified_files: string[];
}

// ─── Bulk Artifact Operations ────────────────────────────────

export interface BulkExportRequest {
  artifact_ids: string[];
  target_collection_id?: string;
  new_collection_name?: string;
  new_collection_description?: string;
  new_collection_type?: CollectionType;
}

export interface BulkExportResult {
  target_collection_id: string;
  target_collection_name: string;
  exported: number;
}

export interface BulkDeleteResult {
  deleted: number;
}

// ─── GitHub Export ───────────────────────────────────────────

export interface GitHubExportRequest {
  repo: string;
  base_branch?: string;
  new_branch?: string;
  commit_message?: string;
  pr_title?: string;
  pr_body?: string;
  github_token: string;
}

export interface GitHubExportResult {
  pr_url: string;
  pr_number: number;
  branch: string;
  files_exported: number;
  skipped_model_configs: number;
}

// ─── Artifact Update Types ───────────────────────────────────

export interface ArtifactUpdate {
  name?: string;
  artifact_type?: ArtifactType;
  version?: string;
  priority?: number;
  target_compatibility?: string[];
  tags?: string[];
  description?: string;
  body?: string;
  file_path?: string;
  handoff_to?: string[] | null;
  is_enabled?: boolean;
}

// ─── Artifact Create Type ─────────────────────────────────────

export interface ArtifactCreate {
  artifact_type: ArtifactType;
  name: string;
  version?: string;
  priority?: number;
  target_compatibility?: string[];
  tags?: string[];
  description?: string;
  body: string;
  file_path: string;
  handoff_to?: string[] | null;
}

// ─── Auth Types ──────────────────────────────────────────────

export type Role = 'user' | 'moderator' | 'admin';

export interface User {
  id: string;
  email: string;
  display_name: string;
  avatar_url?: string;
  is_active: boolean;
  is_admin: boolean;
  role: Role;
  notify_on_download?: boolean;
  notify_on_comment?: boolean;
  mfa_enabled?: boolean;
  created_at: string;
}

export interface UserRegister {
  email: string;
  password: string;
  display_name: string;
}

export interface UserLogin {
  email: string;
  password: string;
}

export interface AuthProviders {
  oidc: boolean;
  github: boolean;
  google: boolean;
}

export interface ApiToken {
  id: string;
  user_id: string;
  name: string;
  token_prefix: string;
  last_used_at?: string;
  expires_at: string;
  is_active: boolean;
  created_at: string;
}

export interface ApiTokenCreate {
  name: string;
  expires_at?: string;
}

// ─── Adapter Types ───────────────────────────────────────────

export interface AdapterInfo {
  name: string;
  description: string;
  targets: string[];
  enabled: boolean;
}

// ─── Doc Cache Types ──────────────────────────────────────────

export interface DocCacheEntry {
  id: string;
  framework: string;
  url: string;
  content_type: string;
  fetched_at: string;
  expires_at: string;
}

export interface DocCacheRefreshResult {
  refreshed: Record<string, number>;
  total_updated: number;
}

// ─── Community / Publish Types ────────────────────────────────

export interface PublishRequest {
  category: string;
  publish_name?: string;
  publish_description?: string;
}

export interface CommunityCollectionsResponse {
  items: Collection[];
  total: number;
}

export interface ImportCommunityResult {
  collection_id: string;
  collection_name: string;
  artifacts_imported: number;
}

// ─── Public Demo Types ────────────────────────────────────────

// Mirrors backend DemoCompileResponse (POST /demo/compile) — the only
// unauthenticated compile route in the API (AGENTS.md rule 13's
// documented exception, see docs/adr/0011-public-demo-sandbox.md).
// Nothing here is persisted; `targets` is a fixed, small subset of the
// full adapter registry (claude-code, cursor, opencode).
export interface DemoCompileResult {
  artifact_count: number;
  targets: Record<string, Record<string, string>>;
}

// ─── Admin Types ──────────────────────────────────────────────

export interface UserAdminInfo {
  id: string;
  email: string;
  display_name: string;
  is_admin: boolean;
  is_active: boolean;
  role: Role;
  created_at: string;
}

// ─── System Settings Types ────────────────────────────────────

export interface SystemSettings {
  oidc_enabled: boolean;
  github_enabled: boolean;
  google_enabled: boolean;
  allow_registration: boolean;
  mfa_enabled: boolean;
  mfa_forced: boolean;
  doc_cache_ttl_days: number;
  disabled_adapters: string[];
  smtp_enabled: boolean;
  smtp_host: string | null;
  smtp_port: number | null;
  smtp_username: string | null;
  smtp_password_set: boolean;
  smtp_from_email: string | null;
  smtp_from_name: string | null;
  smtp_use_tls: boolean | null;
  oidc_client_id: string | null;
  oidc_client_secret_set: boolean;
  oidc_issuer_url: string | null;
  oidc_scopes: string | null;
  github_client_id: string | null;
  github_client_secret_set: boolean;
  google_client_id: string | null;
  google_client_secret_set: boolean;
  updated_at: string;
}

export interface SystemSettingsUpdate {
  oidc_enabled?: boolean;
  github_enabled?: boolean;
  google_enabled?: boolean;
  allow_registration?: boolean;
  mfa_enabled?: boolean;
  mfa_forced?: boolean;
  doc_cache_ttl_days?: number;
  smtp_enabled?: boolean;
  smtp_host?: string;
  smtp_port?: number;
  smtp_username?: string;
  smtp_password?: string;
  smtp_from_email?: string;
  smtp_from_name?: string;
  smtp_use_tls?: boolean;
  oidc_client_id?: string;
  oidc_client_secret?: string;
  oidc_issuer_url?: string;
  oidc_scopes?: string;
  github_client_id?: string;
  github_client_secret?: string;
  google_client_id?: string;
  google_client_secret?: string;
}

export interface SmtpTestOverrides {
  host?: string;
  port?: number;
  username?: string;
  password?: string;
  from_email?: string;
  from_name?: string;
  use_tls?: boolean;
}

export interface OAuthTestOverrides {
  client_id?: string;
  client_secret?: string;
  issuer_url?: string;
  scopes?: string;
}

// ─── User Settings Types ──────────────────────────────────────

export interface UserUpdate {
  display_name?: string;
  email?: string;
  notify_on_download?: boolean;
  notify_on_comment?: boolean;
}

export interface PasswordChange {
  current_password: string;
  new_password: string;
}

export interface ForgotPasswordRequest {
  email: string;
}

export interface ResetPasswordRequest {
  token: string;
  new_password: string;
}

export interface MfaSetupResult {
  secret: string;
  provisioning_uri: string;
}

export interface MfaVerifyResult {
  message: string;
  mfa_enabled: boolean;
}

export interface LoginMfaResponse {
  mfa_required: boolean;
  mfa_token: string;
  message: string;
}
