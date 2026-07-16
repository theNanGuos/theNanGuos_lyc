import { defineStore } from 'pinia'
import { api, type Generation, type GenerationPreview } from '../api/client'

export type DefaultField = 'language' | 'instrumental' | 'vocal_gender' | 'suno_model'
export interface GenerationSettings extends Record<string, unknown> {
  language: string
  instrumental: boolean
  vocal_gender: string
  suno_model: string
  title: string
  retentionLimit?: 1 | 2 | null
  negativeTags?: string
  styleWeight?: number
  weirdnessConstraint?: number
  audioWeight?: number
}

export function buildGenerationPayload(input: { prompt: string; settings: GenerationSettings; savedFields: DefaultField[] }) {
  const { title, retentionLimit = 1, negativeTags, styleWeight, weirdnessConstraint, audioWeight, ...base } = input.settings
  return {
    prompt: input.prompt.trim(),
    retention_limit: retentionLimit,
    overrides: {
      ...base,
      ...(title.trim() ? { title: title.trim() } : {}),
      ...(negativeTags !== undefined ? { negative_tags: negativeTags } : {}),
      ...(styleWeight !== undefined ? { style_weight: styleWeight } : {}),
      ...(weirdnessConstraint !== undefined ? { weirdness_constraint: weirdnessConstraint } : {}),
      ...(audioWeight !== undefined ? { audio_weight: audioWeight } : {}),
    },
    save_defaults: [...input.savedFields],
  }
}

const STATUS_COPY: Record<string, string> = {
  queued: '任务已创建', planning: '理解创作需求', lyrics: '生成歌词', music: '规划曲式与和弦', arrangement: '设计编曲与风格',
  generating: '生成中',
  PENDING: 'Suno 正在准备', TEXT_SUCCESS: '歌词与描述已完成', FIRST_SUCCESS: '第一首已完成，等待全部结果',
  SUCCESS: '歌曲已生成', completed: '已完成', stopped: '已停止等待', stopped_waiting: '已停止等待',
  interrupted: '服务已重启，需继续查询', service_restarted: '服务已重启，需继续查询', failed: '生成失败',
}
export const generationStatusCopy = (status: string) => STATUS_COPY[status] ?? status.replaceAll('_', ' ')

export type GenerationStatus = 'completed' | 'generating' | 'stopped' | 'failed' | 'interrupted'
export function normalizeGenerationStatus(status: string): GenerationStatus {
  if (status === 'completed' || status === 'SUCCESS') return 'completed'
  if (status === 'stopped' || status === 'stopped_waiting') return 'stopped'
  if (status === 'interrupted' || status === 'service_restarted') return 'interrupted'
  if (status === 'failed') return 'failed'
  return 'generating'
}
export const isTerminalGenerationStatus = (status: string) => ['completed', 'stopped', 'failed', 'interrupted'].includes(normalizeGenerationStatus(status))

const SUNO_PROGRESS_RANGES: Record<string, readonly [number, number]> = {
  PENDING: [55, 64],
  TEXT_SUCCESS: [65, 79],
  FIRST_SUCCESS: [80, 94],
}

export function estimatedGenerationProgress(stage: string, backendProgress: number, elapsedSeconds: number) {
  if (stage === 'SUCCESS' || backendProgress >= 100) return 100
  const range = SUNO_PROGRESS_RANGES[stage]
  if (!range) return backendProgress
  const [minimum, maximum] = range
  const animated = minimum + Math.floor(Math.max(0, elapsedSeconds) / 5)
  return Math.min(maximum, Math.max(minimum, backendProgress, animated))
}

export const useGenerationStore = defineStore('generation', {
  state: () => ({ current: null as Generation | null, currentPreview: null as GenerationPreview | null, previewPrompt: '', items: [] as Generation[], loading: false, previewLoading: false, error: '' }),
  actions: {
    async loadPreview(payload: { prompt: string; overrides: Record<string, unknown> }) {
      this.previewLoading = true; this.error = ''
      try {
        this.currentPreview = await api.createPreview(payload)
        this.previewPrompt = payload.prompt
        return this.currentPreview
      } catch (error) {
        this.error = error instanceof Error ? error.message : '创作方案生成失败'
        throw error
      } finally { this.previewLoading = false }
    },
    clearPreview() { this.currentPreview = null; this.previewPrompt = '' },
    async create(payload: ReturnType<typeof buildGenerationPayload>) {
      this.loading = true; this.error = ''
      try { return await api.createGeneration(payload) } catch (error) { this.error = error instanceof Error ? error.message : '提交失败'; throw error } finally { this.loading = false }
    },
    async load(id: string) { this.current = await api.getGeneration(id); return this.current },
    async list(params = '') {
      this.error = ''
      try { this.items = (await api.listGenerations(params)).items; return this.items }
      catch (error) { this.error = error instanceof Error ? error.message : '作品加载失败'; throw error }
    },
    async stop(id: string) { await api.stopWaiting(id); await this.load(id) },
    async resume(id: string) { await api.resumePolling(id); await this.load(id) },
    async remove(id: string) {
      this.error = ''
      try { await api.deleteGeneration(id); this.items = this.items.filter(item => item.request_id !== id) }
      catch (error) { this.error = error instanceof Error ? error.message : '删除失败'; throw error }
    },
  },
})
