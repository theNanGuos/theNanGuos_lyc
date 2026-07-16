export interface Candidate {
  audio_id: string
  title: string
  duration?: number | null
  audio_url: string
  download_url: string
  cover_url: string
  model_name?: string | null
  tags?: string | null
  create_time?: string | null
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
  settings?: Partial<UserDefaults>
  retention_limit?: 1 | 2 | null
  stage_events?: StageEvent[]
  created_at: string
  updated_at: string
}

export interface StageEvent {
  stage: string
  status: string
  progress: number
  at: string
}

export interface SongSpec {
  title: string
  language: string
  genre: string
  mood: string[]
  duration_seconds: number
  vocal: { enabled: boolean; gender: 'male' | 'female' | null }
  tempo: { bpm: number; feel: string }
  key: string
  structure: string[]
  constraints: { explicit: boolean; avoid: string[] }
}

export interface GenerationPreview {
  preview_id: string
  song_spec: SongSpec
  task_plan: { goal: string; steps: Array<Record<string, unknown>> }
}

async function request<T>(url: string, init?: RequestInit): Promise<T> {
  const response = await fetch(url, { headers: { 'Content-Type': 'application/json', ...init?.headers }, ...init })
  if (!response.ok) {
    let message = `请求失败（${response.status}）`
    try {
      const detail = (await response.json()).detail
      if (typeof detail === 'string') message = detail
      else if (Array.isArray(detail)) message = detail.map(item => `${Array.isArray(item?.loc) ? item.loc.join('.') + ': ' : ''}${item?.msg || String(item)}`).join('；')
    } catch { /* non-JSON error */ }
    throw new Error(message)
  }
  if (response.status === 204) return undefined as T
  return response.json() as Promise<T>
}

export const api = {
  createPreview: (payload: unknown) => request<GenerationPreview>('/api/generation-previews', { method: 'POST', body: JSON.stringify(payload) }),
  createGeneration: (payload: unknown) => request<{ request_id: string; status: string }>('/api/generations', { method: 'POST', body: JSON.stringify(payload) }),
  listGenerations: (params = '') => request<{ items: Generation[] }>(`/api/generations${params}`),
  getGeneration: (id: string) => request<Generation>(`/api/generations/${id}`),
  stopWaiting: (id: string) => request(`/api/generations/${id}/stop-waiting`, { method: 'POST' }),
  resumePolling: (id: string) => request(`/api/generations/${id}/resume-polling`, { method: 'POST' }),
  deleteGeneration: (id: string) => request<void>(`/api/generations/${id}`, { method: 'DELETE' }),
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
