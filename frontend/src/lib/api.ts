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
};
