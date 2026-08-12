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
  source_collection_id?: string;
  source_collection_name?: string;
}

// ─── Collection Types ────────────────────────────────────────

export type CollectionType = 'base' | 'additional';
export type Visibility = 'private' | 'public';

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
  last_synced_at?: string;
  created_at: string;
  updated_at: string;
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

export interface CompileResult {
  profile_id: string;
  profile_name: string;
  target: string;
  artifact_count: number;
  files: Record<string, string>;
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
  is_enabled?: boolean;
}

// ─── Auth Types ──────────────────────────────────────────────

export interface User {
  id: string;
  email: string;
  display_name: string;
  avatar_url?: string;
  is_active: boolean;
  is_admin: boolean;
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
  github_token: string;
}

export interface PublishResult {
  pr_url: string;
  pr_number: number;
  branch: string;
  published: boolean;
}

export interface ImportCommunityResult {
  collection_id: string;
  collection_name: string;
  artifacts_imported: number;
}

// ─── Admin Types ──────────────────────────────────────────────

export interface UserAdminInfo {
  id: string;
  email: string;
  display_name: string;
  is_admin: boolean;
  is_active: boolean;
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
}

// ─── User Settings Types ──────────────────────────────────────

export interface UserUpdate {
  display_name?: string;
  email?: string;
}

export interface PasswordChange {
  current_password: string;
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
