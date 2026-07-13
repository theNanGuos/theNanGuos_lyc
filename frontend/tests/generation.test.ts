import { setActivePinia, createPinia } from 'pinia'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { buildGenerationPayload, generationStatusCopy, isTerminalGenerationStatus, normalizeGenerationStatus } from '../src/stores/generation'
import * as generationHelpers from '../src/stores/generation'
import { usePlayerStore } from '../src/stores/player'
import { demoGeneration, sortGenerations } from '../src/data/demo'
import { usePreferencesStore } from '../src/stores/preferences'

describe('generation helpers', () => {
  it('only persists explicitly selected default fields', () => {
    expect(buildGenerationPayload({
      prompt: '深夜学习的中文 lo-fi',
      settings: { language: 'zh', instrumental: false, vocal_gender: 'f', suno_model: 'V5', title: '深夜微光', negativeTags: '重鼓点', styleWeight: .7, weirdnessConstraint: .3, audioWeight: .5 },
      savedFields: ['language', 'vocal_gender', 'suno_model'],
    })).toEqual({
      prompt: '深夜学习的中文 lo-fi',
      overrides: { language: 'zh', instrumental: false, vocal_gender: 'f', suno_model: 'V5', title: '深夜微光', negative_tags: '重鼓点', style_weight: .7, weirdness_constraint: .3, audio_weight: .5 },
      save_defaults: ['language', 'vocal_gender', 'suno_model'],
    })
  })

  it('omits an empty optional title from generation overrides', () => {
    const payload = buildGenerationPayload({
      prompt: '  深夜学习的中文 lo-fi  ',
      settings: { language: 'zh', instrumental: false, vocal_gender: 'f', suno_model: 'V5', title: '   ' },
      savedFields: [],
    })
    expect(payload.prompt).toBe('深夜学习的中文 lo-fi')
    expect(payload.overrides).not.toHaveProperty('title')
  })

  it('maps FIRST_SUCCESS to the confirmed user-facing copy', () => {
    expect(generationStatusCopy('FIRST_SUCCESS')).toBe('第一首已完成，等待全部结果')
    expect(generationStatusCopy('service_restarted')).toBe('服务已重启，需继续查询')
  })

  it('provides complete route-specific demo states', () => {
    expect(demoGeneration('demo-a')?.candidates).toHaveLength(2)
    expect(demoGeneration('demo-c')).toMatchObject({ progress: 80, stage: 'FIRST_SUCCESS', status: 'generating' })
  })

  it('maps generating and sorts work records by creation time', () => {
    expect(generationStatusCopy('generating')).toBe('生成中')
    const items = [demoGeneration('demo-a')!, demoGeneration('demo-b')!]
    expect(sortGenerations(items, 'oldest')[0].request_id).toBe('demo-b')
    expect(sortGenerations(items, 'newest')[0].request_id).toBe('demo-a')
  })

  it('normalizes backend lifecycle states and identifies terminal states', () => {
    expect(normalizeGenerationStatus('queued')).toBe('generating')
    expect(normalizeGenerationStatus('running')).toBe('generating')
    expect(normalizeGenerationStatus('stopped_waiting')).toBe('stopped')
    expect(normalizeGenerationStatus('service_restarted')).toBe('interrupted')
    expect(isTerminalGenerationStatus('failed')).toBe(true)
    expect(isTerminalGenerationStatus('stopped')).toBe(true)
    expect(isTerminalGenerationStatus('interrupted')).toBe(true)
    expect(isTerminalGenerationStatus('running')).toBe(false)
  })

  it('animates estimated progress inside real Suno stage boundaries', () => {
    const estimate = (generationHelpers as unknown as {
      estimatedGenerationProgress: (stage: string, backendProgress: number, elapsedSeconds: number) => number
    }).estimatedGenerationProgress
    expect(typeof estimate).toBe('function')
    expect(estimate('PENDING', 55, 0)).toBe(55)
    expect(estimate('PENDING', 55, 20)).toBe(59)
    expect(estimate('PENDING', 55, 999)).toBe(64)
    expect(estimate('TEXT_SUCCESS', 65, 999)).toBe(79)
    expect(estimate('FIRST_SUCCESS', 80, 999)).toBe(94)
    expect(estimate('SUCCESS', 100, 0)).toBe(100)
  })
})

describe('player store', () => {
  beforeEach(() => setActivePinia(createPinia()))

  it('toggles the selected candidate and resets progress', () => {
    const player = usePlayerStore()
    player.select({ requestId: 'one', audioId: 'a', title: '深夜微光 A', subtitle: 'lo-fi pop · 女声', audioUrl: '/a', coverUrl: '/cover' })
    expect(player.playing).toBe(true)
    player.currentTime = 21
    player.select({ requestId: 'one', audioId: 'b', title: '深夜微光 B', subtitle: 'lo-fi pop · 女声', audioUrl: '/b', coverUrl: '/cover-b' })
    expect(player.current?.audioId).toBe('b')
    expect(player.currentTime).toBe(0)
    player.toggle()
    expect(player.playing).toBe(false)
  })
})

describe('preferences store', () => {
  beforeEach(() => setActivePinia(createPinia()))

  it('keeps system defaults when an empty profile returns null fields', async () => {
    vi.stubGlobal('fetch', vi.fn(async () => new Response(JSON.stringify({
      defaults: { language: null, instrumental: null, vocal_gender: null, suno_model: null },
      style_markdown: '',
    }), { status: 200 })))
    const preferences = usePreferencesStore()
    await preferences.load()
    expect(preferences.defaults).toEqual({ language: 'zh', instrumental: false, vocal_gender: 'f', suno_model: 'V5' })
    preferences.defaults.language = 'en'
    preferences.restoreSystemDefaults()
    expect(preferences.defaults.language).toBe('zh')
  })
})
