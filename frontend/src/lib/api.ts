/**
 * MyACE API client — typed fetch wrapper for the backend API.
 */

const API_BASE = '/api/v1';

async function request<T>(
  endpoint: string,
  options: RequestInit = {},
): Promise<T> {
  const token = localStorage.getItem('myace_token');
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(options.headers as Record<string, string>),
  };

  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  const response = await fetch(`${API_BASE}${endpoint}`, {
    ...options,
    headers,
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: response.statusText }));
    throw new Error(error.detail || `HTTP ${response.status}`);
  }

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

  create: (data: import('@/types').CollectionCreate, ownerId: string) =>
    request<import('@/types').Collection>('/collections', {
      method: 'POST',
      body: JSON.stringify(data),
      headers: { 'X-User-Id': ownerId },
    }),

  getArtifacts: (collectionId: string, type?: string) => {
    const qs = type ? `?type=${type}` : '';
    return request<import('@/types').Artifact[]>(`/collections/${collectionId}/artifacts${qs}`);
  },

  delete: (id: string, ownerId: string) =>
    request<void>(`/collections/${id}`, {
      method: 'DELETE',
      headers: { 'X-User-Id': ownerId },
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

  create: (data: import('@/types').ProfileCreate, ownerId: string) =>
    request<import('@/types').Profile>('/profiles', {
      method: 'POST',
      body: JSON.stringify(data),
      headers: { 'X-User-Id': ownerId },
    }),

  update: (id: string, data: import('@/types').ProfileCreate, ownerId: string) =>
    request<import('@/types').Profile>(`/profiles/${id}`, {
      method: 'PUT',
      body: JSON.stringify(data),
      headers: { 'X-User-Id': ownerId },
    }),

  compile: (data: import('@/types').ProfileCompileRequest) =>
    request<import('@/types').CompileResult>('/profiles/compile', {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  delete: (id: string, ownerId: string) =>
    request<void>(`/profiles/${id}`, {
      method: 'DELETE',
      headers: { 'X-User-Id': ownerId },
    }),
};

// ─── Adapters ────────────────────────────────────────────────

export const adaptersApi = {
  list: () =>
    request<import('@/types').AdapterInfo[]>('/adapters'),

  get: (name: string) =>
    request<import('@/types').AdapterInfo>(`/adapters/${name}`),
};

// ─── Auth ────────────────────────────────────────────────────

export const authApi = {
  login: (provider: string) => {
    window.location.href = `${API_BASE}/auth/login/${provider}`;
  },

  createToken: (data: import('@/types').ApiTokenCreate, userId: string) =>
    request<import('@/types').ApiToken & { token?: string }>('/auth/tokens', {
      method: 'POST',
      body: JSON.stringify(data),
      headers: { 'X-User-Id': userId },
    }),

  listTokens: (userId: string) =>
    request<import('@/types').ApiToken[]>(`/auth/tokens?user_id=${userId}`),

  revokeToken: (tokenId: string, userId: string) =>
    request<void>(`/auth/tokens/${tokenId}`, {
      method: 'DELETE',
      headers: { 'X-User-Id': userId },
    }),
};
