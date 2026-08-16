/**
 * MyACE API client — typed fetch wrapper for the backend API.
 */

const API_BASE = '/api/v1';

async function request<T>(
  endpoint: string,
  options: RequestInit = {},
): Promise<T> {
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(options.headers as Record<string, string>),
  };

  const response = await fetch(`${API_BASE}${endpoint}`, {
    ...options,
    headers,
    credentials: 'same-origin',
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: response.statusText }));
    throw new Error(error.detail || `HTTP ${response.status}`);
  }

  if (response.status === 204) return undefined as T;
  return response.json();
}

// ─── Collections ─────────────────────────────────────────────

export const collectionsApi = {
  list: (params?: { owner_id?: string; type?: string; visibility?: string }) => {
    const searchParams = new URLSearchParams();
    if (params?.owner_id) searchParams.set('owner_id', params.owner_id);
    if (params?.type) searchParams.set('type', params.type);
    if (params?.visibility) searchParams.set('visibility', params.visibility);
    const qs = searchParams.toString();
    return request<import('@/types').Collection[]>(`/collections${qs ? `?${qs}` : ''}`);
  },

  get: (id: string) =>
    request<import('@/types').Collection>(`/collections/${id}`),

  update: (id: string, data: import('@/types').CollectionUpdate) =>
    request<import('@/types').Collection>(`/collections/${id}`, {
      method: 'PATCH',
      body: JSON.stringify(data),
    }),

  getArtifacts: (collectionId: string, params?: { type?: string; include_disabled?: boolean }) => {
    const searchParams = new URLSearchParams();
    if (params?.type) searchParams.set('type', params.type);
    if (params?.include_disabled) searchParams.set('include_disabled', 'true');
    const qs = searchParams.toString();
    return request<import('@/types').Artifact[]>(`/collections/${collectionId}/artifacts${qs ? `?${qs}` : ''}`);
  },

  getArtifact: (collectionId: string, artifactId: string) =>
    request<import('@/types').Artifact>(`/collections/${collectionId}/artifacts/${artifactId}`),

  updateArtifact: (collectionId: string, artifactId: string, data: import('@/types').ArtifactUpdate) =>
    request<import('@/types').Artifact>(`/collections/${collectionId}/artifacts/${artifactId}`, {
      method: 'PATCH',
      body: JSON.stringify(data),
    }),

  delete: (id: string) =>
    request<void>(`/collections/${id}`, { method: 'DELETE' }),

  bulkDeleteArtifacts: (collectionId: string, artifactIds: string[]) =>
    request<import('@/types').BulkDeleteResult>(`/collections/${collectionId}/artifacts/bulk-delete`, {
      method: 'POST',
      body: JSON.stringify({ artifact_ids: artifactIds }),
    }),

  bulkExportArtifacts: (collectionId: string, data: import('@/types').BulkExportRequest) =>
    request<import('@/types').BulkExportResult>(`/collections/${collectionId}/artifacts/bulk-export`, {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  exportToGithub: (collectionId: string, data: import('@/types').GitHubExportRequest) =>
    request<import('@/types').GitHubExportResult>(`/collections/${collectionId}/export/github`, {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  // ─── Community / Publish ─────────────────────────────────

  publish: (collectionId: string, data: import('@/types').PublishRequest) =>
    request<import('@/types').Collection>(`/collections/${collectionId}/publish`, {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  listCommunity: (params?: { type?: string; category?: string; offset?: number; limit?: number }) => {
    const searchParams = new URLSearchParams();
    if (params?.type) searchParams.set('type', params.type);
    if (params?.category) searchParams.set('category', params.category);
    if (params?.offset !== undefined) searchParams.set('offset', String(params.offset));
    if (params?.limit !== undefined) searchParams.set('limit', String(params.limit));
    const qs = searchParams.toString();
    return request<import('@/types').CommunityCollectionsResponse>(`/collections/community${qs ? `?${qs}` : ''}`);
  },

  listCommunityTop: (limit?: number) => {
    const qs = limit ? `?limit=${limit}` : '';
    return request<import('@/types').Collection[]>(`/collections/community/top${qs}`);
  },

  listCommunityCategories: () =>
    request<string[]>('/collections/community/categories'),

  importCommunity: (collectionId: string) =>
    request<import('@/types').ImportCommunityResult>(`/collections/${collectionId}/import`, {
      method: 'POST',
    }),
};

// ─── Profiles ────────────────────────────────────────────────

export const profilesApi = {
  list: (params?: { owner_id?: string; is_public?: boolean }) => {
    const searchParams = new URLSearchParams();
    if (params?.owner_id) searchParams.set('owner_id', params.owner_id);
    if (params?.is_public !== undefined) searchParams.set('is_public', String(params.is_public));
    const qs = searchParams.toString();
    return request<import('@/types').Profile[]>(`/profiles${qs ? `?${qs}` : ''}`);
  },

  get: (id: string) =>
    request<import('@/types').Profile>(`/profiles/${id}`),

  create: (data: import('@/types').ProfileCreate) =>
    request<import('@/types').Profile>('/profiles', {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  update: (id: string, data: import('@/types').ProfileCreate) =>
    request<import('@/types').Profile>(`/profiles/${id}`, {
      method: 'PUT',
      body: JSON.stringify(data),
    }),

  compile: (data: import('@/types').ProfileCompileRequest) =>
    request<import('@/types').CompileResult>('/profiles/compile', {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  delete: (id: string) =>
    request<void>(`/profiles/${id}`, { method: 'DELETE' }),
};

// ─── Adapters ────────────────────────────────────────────────

export const adaptersApi = {
  list: () =>
    request<import('@/types').AdapterInfo[]>('/adapters'),

  get: (name: string) =>
    request<import('@/types').AdapterInfo>(`/adapters/${name}`),
};

// ─── Doc Cache ───────────────────────────────────────────────

export const docCacheApi = {
  list: (framework?: string) => {
    const qs = framework ? `?framework=${encodeURIComponent(framework)}` : '';
    return request<import('@/types').DocCacheEntry[]>(`/doc-cache${qs}`);
  },

  refresh: () =>
    request<import('@/types').DocCacheRefreshResult>('/doc-cache/refresh', {
      method: 'POST',
    }),

  delete: (id: string) =>
    request<void>(`/doc-cache/${id}`, { method: 'DELETE' }),
};

// ─── Auth ────────────────────────────────────────────────────

export const authApi = {
  register: (data: import('@/types').UserRegister) =>
    request<import('@/types').User>('/auth/register', {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  login: (data: import('@/types').UserLogin) =>
    request<import('@/types').User>('/auth/login', {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  logout: () =>
    request<{ message: string }>('/auth/logout', { method: 'POST' }),

  me: () =>
    request<import('@/types').User>('/auth/me'),

  providers: () =>
    request<import('@/types').AuthProviders>('/auth/providers'),

  loginWithProvider: (provider: string) => {
    window.location.href = `${API_BASE}/auth/login/${provider}`;
  },

  createToken: (data: import('@/types').ApiTokenCreate) =>
    request<import('@/types').ApiToken & { token?: string }>('/auth/tokens', {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  listTokens: () =>
    request<import('@/types').ApiToken[]>('/auth/tokens'),

  revokeToken: (tokenId: string) =>
    request<void>(`/auth/tokens/${tokenId}`, { method: 'DELETE' }),

  listUsers: () =>
    request<import('@/types').UserAdminInfo[]>('/auth/users'),

  setUserActive: (userId: string, isActive: boolean) =>
    request<{ id: string; is_active: boolean }>(
      `/auth/users/${userId}?is_active=${isActive}`,
      { method: 'PATCH' },
    ),

  setUserRole: (userId: string, role: import('@/types').Role) =>
    request<{ id: string; role: import('@/types').Role; is_admin: boolean }>(
      `/auth/users/${userId}/role`,
      { method: 'PATCH', body: JSON.stringify({ role }) },
    ),

  removeUser: (userId: string) =>
    request<{ message: string }>(`/auth/users/${userId}`, { method: 'DELETE' }),

  updateProfile: (data: import('@/types').UserUpdate) =>
    request<import('@/types').User>('/auth/me', {
      method: 'PATCH',
      body: JSON.stringify(data),
    }),

  changePassword: (data: import('@/types').PasswordChange) =>
    request<{ message: string }>('/auth/me/password', {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  deleteAccount: () =>
    request<{ message: string }>('/auth/me', { method: 'DELETE' }),

  forgotPassword: (data: import('@/types').ForgotPasswordRequest) =>
    request<{ message: string }>('/auth/forgot-password', {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  resetPassword: (data: import('@/types').ResetPasswordRequest) =>
    request<{ message: string }>('/auth/reset-password', {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  setupTotp: () =>
    request<import('@/types').MfaSetupResult>('/auth/me/mfa/totp/setup', {
      method: 'POST',
    }),

  verifyTotp: (code: string) =>
    request<import('@/types').MfaVerifyResult>(`/auth/me/mfa/totp/verify?code=${encodeURIComponent(code)}`, {
      method: 'POST',
    }),

  disableTotp: (code: string) =>
    request<{ message: string }>(`/auth/me/mfa/totp/disable?code=${encodeURIComponent(code)}`, {
      method: 'POST',
    }),
};

// ─── Admin API ────────────────────────────────────────────────

export const adminApi = {
  getSettings: () =>
    request<import('@/types').SystemSettings>('/admin/settings'),

  updateSettings: (data: import('@/types').SystemSettingsUpdate) =>
    request<import('@/types').SystemSettings>('/admin/settings', {
      method: 'PATCH',
      body: JSON.stringify(data),
    }),

  toggleAdapter: (name: string, enabled: boolean) =>
    request<{ name: string; enabled: boolean }>(
      `/admin/adapters/${encodeURIComponent(name)}?enabled=${enabled}`,
      { method: 'PATCH' },
    ),

  testSmtp: (overrides?: import('@/types').SmtpTestOverrides) =>
    request<{ message: string }>('/admin/settings/smtp/test', {
      method: 'POST',
      body: JSON.stringify(overrides ?? {}),
    }),

  testOAuthProvider: (provider: string, overrides?: import('@/types').OAuthTestOverrides) =>
    request<{ message: string }>(`/admin/settings/oauth/${provider}/test`, {
      method: 'POST',
      body: JSON.stringify(overrides ?? {}),
    }),
};

// ─── Moderation API ──────────────────────────────────────────

export const moderationApi = {
  getQueue: () =>
    request<import('@/types').ModerationQueueItem[]>('/moderation/queue'),

  approve: (collectionId: string) =>
    request<import('@/types').Collection>(`/moderation/${collectionId}/approve`, {
      method: 'POST',
    }),

  deny: (collectionId: string, reason: string) =>
    request<import('@/types').Collection>(`/moderation/${collectionId}/deny`, {
      method: 'POST',
      body: JSON.stringify({ reason }),
    }),

  updateMeta: (
    collectionId: string,
    data: { name?: string; description?: string; category?: string },
  ) =>
    request<import('@/types').Collection>(`/moderation/${collectionId}/meta`, {
      method: 'PATCH',
      body: JSON.stringify(data),
    }),
};
