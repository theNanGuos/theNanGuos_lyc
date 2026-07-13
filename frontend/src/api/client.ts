export interface Candidate {
  audio_id: string
  title: string
  duration?: number | null
  audio_url: string
  download_url: string
  cover_url: string
}

export interface Generation {
  request_id: string
  user_request: string
  status: string
  stage: string
  progress: number
  task_id?: string | null
  error?: { code?: string; message?: string } | null
  candidates: Candidate[]
  created_at: string
  updated_at: string
}

async function request<T>(url: string, init?: RequestInit): Promise<T> {
  const response = await fetch(url, { headers: { 'Content-Type': 'application/json', ...init?.headers }, ...init })
  if (!response.ok) {
    let message = `请求失败（${response.status}）`
    try { message = (await response.json()).detail ?? message } catch { /* non-JSON error */ }
    throw new Error(message)
  }
  if (response.status === 204) return undefined as T
  return response.json() as Promise<T>
}

export const api = {
  createGeneration: (payload: unknown) => request<{ request_id: string; status: string }>('/api/generations', { method: 'POST', body: JSON.stringify(payload) }),
  listGenerations: (params = '') => request<{ items: Generation[] }>(`/api/generations${params}`),
  getGeneration: (id: string) => request<Generation>(`/api/generations/${id}`),
  stopWaiting: (id: string) => request(`/api/generations/${id}/stop-waiting`, { method: 'POST' }),
  resumePolling: (id: string) => request(`/api/generations/${id}/resume-polling`, { method: 'POST' }),
  getPreferences: () => request<{ defaults: UserDefaults; style_markdown: string }>('/api/preferences'),
  saveDefaults: (defaults: UserDefaults) => request<UserDefaults>('/api/preferences/defaults', { method: 'PUT', body: JSON.stringify(defaults) }),
  saveStyle: (markdown: string) => request('/api/preferences/style', { method: 'PUT', body: JSON.stringify({ markdown }) }),
  clearPreferences: () => request<void>('/api/preferences', { method: 'DELETE' }),
}

export interface UserDefaults {
  language: string
  instrumental: boolean
  vocal_gender: string | null
  suno_model: string
}
