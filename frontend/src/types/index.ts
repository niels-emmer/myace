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
  last_synced_at?: string;
  created_at: string;
  updated_at: string;
}

export interface CollectionUpdate {
  name?: string;
  description?: string;
  collection_type?: CollectionType;
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
}
