import { mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createMemoryHistory, createRouter } from 'vue-router'

import CreatePage from '../src/pages/CreatePage.vue'
import GeneratingPage from '../src/pages/GeneratingPage.vue'
import PreferencesPage from '../src/pages/PreferencesPage.vue'
import ResultPage from '../src/pages/ResultPage.vue'
import WorksPage from '../src/pages/WorksPage.vue'
import { usePreferencesStore } from '../src/stores/preferences'
import { useGenerationStore } from '../src/stores/generation'
import { usePlayerStore } from '../src/stores/player'
import { demoGeneration } from '../src/data/demo'

const testRouter = () => createRouter({ history: createMemoryHistory(), routes: [
  { path: '/', component: { template: '<div />' } },
  { path: '/create', component: { template: '<div />' } },
  { path: '/works', component: { template: '<div />' } },
  { path: '/preferences', component: { template: '<div />' } },
  { path: '/generations/:id', component: GeneratingPage },
  { path: '/generations/:id/result', component: { template: '<div />' } },
] })

describe('creation controls', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.stubGlobal('fetch', vi.fn(async () => new Response(JSON.stringify({ defaults: {}, style_markdown: '' }), { status: 200 })))
  })

  it('starts a new creation with an empty prompt and example placeholder', () => {
    const wrapper = mount(CreatePage, { global: { plugins: [createPinia(), testRouter()] } })
    const prompt = wrapper.get('[aria-label="自然语言创作描述"]')

    expect(prompt.element).toHaveProperty('value', '')
    expect(prompt.attributes('placeholder')).toContain('深夜学习')
    wrapper.unmount()
  })

  it('clears a previous preview when opening a new creation page', async () => {
    const pinia = createPinia()
    setActivePinia(pinia)
    const generation = useGenerationStore()
    generation.currentPreview = {
      preview_id: 'b'.repeat(32),
      song_spec: {
        title: '旧方案', language: 'zh', genre: 'pop', mood: ['warm'], duration_seconds: 90,
        vocal: { enabled: true, gender: 'female' }, tempo: { bpm: 90, feel: 'steady' }, key: 'C major',
        structure: ['verse', 'chorus'], constraints: { explicit: false, avoid: [] },
      },
      task_plan: { goal: 'old', steps: [] },
    }
    generation.previewPrompt = '旧输入'

    const wrapper = mount(CreatePage, { global: { plugins: [pinia, testRouter()] } })
    await Promise.resolve()

    expect(generation.currentPreview).toBeNull()
    expect(generation.previewPrompt).toBe('')
    wrapper.unmount()
  })

  it('keeps advanced Suno parameters collapsed until requested', async () => {
    const router = testRouter()
    const wrapper = mount(CreatePage, { global: { plugins: [createPinia(), router] } })
    expect(wrapper.find('[data-testid="advanced-fields"]').exists()).toBe(false)
    await wrapper.get('[data-testid="advanced-toggle"]').trigger('click')
    expect(wrapper.get('[data-testid="advanced-fields"]').text()).toContain('排除标签')
  })

  it('shows local retention as a one-off setting with a cost warning', () => {
    const wrapper = mount(CreatePage, { global: { plugins: [createPinia(), testRouter()] } })
    const select = wrapper.get('[aria-label="本地保留数量"]')

    expect(select.element).toHaveProperty('value', '1')
    expect(wrapper.get('[data-testid="retention-help"]').text()).toContain('不会减少供应商实际生成数量或费用')
    wrapper.unmount()
  })

  it('previews, edits, and submits the approved conductor plan', async () => {
    const requests: Array<{ url: string; body: Record<string, unknown> }> = []
    vi.stubGlobal('fetch', vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input)
      if (init?.body) requests.push({ url, body: JSON.parse(String(init.body)) })
      if (url.endsWith('/api/preferences')) {
        return new Response(JSON.stringify({ defaults: {}, style_markdown: '' }), { status: 200 })
      }
      if (url.endsWith('/api/generation-previews')) {
        return new Response(JSON.stringify({
          preview_id: 'a'.repeat(32),
          song_spec: {
            title: '雨夜对话', language: 'zh', genre: 'jazz', mood: ['warm'], duration_seconds: 120,
            vocal: { enabled: true, gender: 'male' }, tempo: { bpm: 90, feel: 'swing' }, key: 'C major',
            structure: ['verse', 'chorus'], constraints: { explicit: false, avoid: ['heavy distortion'] },
          },
          task_plan: { goal: 'create jazz', steps: [{ id: 'lyrics', actor: 'LyricsAgent', task: 'write', input_keys: [], output_key: 'lyrics_result', depends_on: [] }] },
        }), { status: 200 })
      }
      if (url === '/api/generations') {
        return new Response(JSON.stringify({ request_id: 'created-1', status: 'queued' }), { status: 202 })
      }
      return new Response(JSON.stringify({
        request_id: 'created-1', user_request: 'jazz', status: 'queued', stage: 'queued', progress: 0,
        candidates: [], stage_events: [], created_at: '2026-07-14T12:00:00', updated_at: '2026-07-14T12:00:00',
      }), { status: 200 })
    }))
    const pinia = createPinia(); const router = testRouter()
    await router.push('/create'); await router.isReady()
    const wrapper = mount(CreatePage, { global: { plugins: [pinia, router] } })

    await wrapper.get('[aria-label="自然语言创作描述"]').setValue('一首雨夜爵士，萨克斯与钢琴对话')
    await wrapper.get('[aria-label="提交描述"]').trigger('click')
    await vi.waitFor(() => expect(wrapper.get('[data-testid="plan-genre"]').element).toBeTruthy())
    expect(wrapper.get('[data-testid="retry-preview-icon"]').attributes('data-icon')).toBe('arrow-path')
    await wrapper.get('[data-testid="plan-genre"]').setValue('neo soul')
    await wrapper.get('[data-testid="plan-duration"]').setValue('150')
    await wrapper.get('[data-testid="confirm-generation"]').trigger('click')

    const previewRequest = requests.find(item => item.url.endsWith('/api/generation-previews'))
    const generationRequest = requests.find(item => item.url === '/api/generations')
    expect(previewRequest?.body).toMatchObject({ prompt: expect.any(String) })
    expect(generationRequest?.body).toMatchObject({
      preview_id: 'a'.repeat(32),
      approved_song_spec: { genre: 'neo soul', duration_seconds: 150, title: '雨夜对话' },
    })
    wrapper.unmount()
  })
})

describe('generation progress', () => {
  it('uses one stable row structure for every local and remote generation step', async () => {
    const pinia = createPinia(); const router = testRouter()
    await router.push('/generations/demo-c?demo=1'); await router.isReady()
    const wrapper = mount(GeneratingPage, { global: { plugins: [pinia, router] } })

    await vi.waitFor(() => expect(wrapper.findAll('[data-testid="generation-step"]')).toHaveLength(6))
    for (const step of wrapper.findAll('[data-testid="generation-step"]')) {
      expect(step.find('.step-index').exists()).toBe(true)
      expect(step.find('.step-marker').exists()).toBe(true)
      expect(step.find('.step-copy').exists()).toBe(true)
    }
    expect(wrapper.find('.generation-main .waveform').exists()).toBe(false)
    wrapper.unmount()
  })

  it('renders the real request and recorded stage times from the API', async () => {
    vi.stubGlobal('fetch', vi.fn(async () => new Response(JSON.stringify({
      request_id: 'real-1',
      user_request: '一首雨夜爵士，萨克斯与钢琴对话',
      status: 'running',
      stage: 'lyrics',
      progress: 20,
      candidates: [],
      stage_events: [
        { stage: 'queued', status: 'queued', progress: 0, at: '2026-07-14T12:30:00' },
        { stage: 'conductor', status: 'running', progress: 5, at: '2026-07-14T12:31:00' },
        { stage: 'lyrics', status: 'running', progress: 20, at: '2026-07-14T12:34:56' },
      ],
      created_at: '2026-07-14T12:30:00',
      updated_at: '2026-07-14T12:34:56',
    }), { status: 200 })))
    const pinia = createPinia(); const router = testRouter()
    await router.push('/generations/real-1'); await router.isReady()

    const wrapper = mount(GeneratingPage, { global: { plugins: [pinia, router] } })

    await vi.waitFor(() => expect(wrapper.get('[data-testid="current-request"]').text()).toContain('一首雨夜爵士'))
    expect(wrapper.get('[role="status"]').attributes('aria-live')).toBe('polite')
    expect(wrapper.get('[role="status"]').text()).toContain('正在生成歌词')
    expect(wrapper.text()).toContain('12:34:56')
    expect(wrapper.text()).not.toContain('中文 lo-fi pop · 温暖克制 · 女声 · 约 90 秒')
    expect(wrapper.text()).not.toContain('10:28:41')
    wrapper.unmount()
  })

  it('does not activate waiting demo data without the explicit demo query', async () => {
    vi.stubGlobal('fetch', vi.fn(async () => new Response(JSON.stringify({
      request_id: 'demo-c', user_request: 'API 等待任务', status: 'running', stage: 'lyrics', progress: 20,
      candidates: [], stage_events: [], created_at: '2026-07-14T12:00:00', updated_at: '2026-07-14T12:01:00',
    }), { status: 200 })))
    const pinia = createPinia(); const router = testRouter()
    await router.push('/generations/demo-c'); await router.isReady()

    const wrapper = mount(GeneratingPage, { global: { plugins: [pinia, router] } })

    await vi.waitFor(() => expect(wrapper.get('[data-testid="current-request"]').text()).toContain('API 等待任务'))
    wrapper.unmount()
  })
})

describe('preference clearing', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.stubGlobal('fetch', vi.fn(async () => new Response(JSON.stringify({ defaults: {}, style_markdown: '' }), { status: 200 })))
  })

  it('requires a second confirmation before clearing preferences', async () => {
    const wrapper = mount(PreferencesPage, { global: { plugins: [createPinia(), testRouter()] } })
    await wrapper.get('[data-testid="clear-preferences"]').trigger('click')
    expect(wrapper.get('[role="dialog"]').text()).toContain('不会删除已生成作品')
    await wrapper.get('[data-testid="cancel-clear"]').trigger('click')
    expect(wrapper.find('[role="dialog"]').exists()).toBe(false)
  })

  it('renders Markdown but escapes embedded HTML', async () => {
    const pinia = createPinia()
    setActivePinia(pinia)
    const preferences = usePreferencesStore()
    const wrapper = mount(PreferencesPage, { global: { plugins: [pinia, testRouter()] } })
    await Promise.resolve()
    preferences.markdown = '# 偏好\n\n- 温暖\n\n<img src=x onerror="alert(1)">'
    await wrapper.get('.editor-tabs button:nth-child(2)').trigger('click')
    expect(wrapper.get('.markdown-preview h1').text()).toBe('偏好')
    expect(wrapper.get('.markdown-preview li').text()).toBe('温暖')
    expect(wrapper.find('.markdown-preview img').exists()).toBe(false)
  })
})

describe('result playback', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.spyOn(HTMLMediaElement.prototype, 'load').mockImplementation(() => undefined)
    vi.spyOn(HTMLMediaElement.prototype, 'play').mockResolvedValue()
    vi.spyOn(HTMLMediaElement.prototype, 'pause').mockImplementation(() => undefined)
    vi.stubGlobal('fetch', vi.fn(async () => new Response(JSON.stringify({ defaults: {}, style_markdown: '' }), { status: 200 })))
  })

  it('binds candidate playback progress and volume to a real audio element', async () => {
    const pinia = createPinia(); const router = testRouter()
    await router.push('/generations/demo-a/result?demo=1'); await router.isReady()
    setActivePinia(pinia)
    useGenerationStore().current = demoGeneration('demo-a') ?? null
    const wrapper = mount(ResultPage, { attachTo: document.body, global: { plugins: [pinia, router] } })
    expect(wrapper.get('[data-testid="candidate-play-a"]').attributes('aria-label')).toContain('播放')
    expect(wrapper.get('[data-testid="candidate-volume-a"]').attributes('aria-label')).toContain('音量')
    await wrapper.get('[data-testid="candidate-play-a"]').trigger('click')
    expect(wrapper.get('[data-testid="candidate-play-a"]').attributes('aria-label')).toContain('暂停')
    const audio = wrapper.get('audio').element as HTMLAudioElement
    expect(audio.getAttribute('src')).toContain('/demo-a/a.mp3')
    await vi.waitFor(() => expect(HTMLMediaElement.prototype.play).toHaveBeenCalled())
    Object.defineProperty(audio, 'duration', { configurable: true, value: 92 })
    Object.defineProperty(audio, 'currentTime', { configurable: true, writable: true, value: 38 })
    await wrapper.get('audio').trigger('loadedmetadata'); await wrapper.get('audio').trigger('timeupdate')
    expect(wrapper.get('[data-testid="candidate-time-a"]').text()).toContain('0:38 / 1:32')
    expect(wrapper.get('[data-testid="candidate-progress-a"]').attributes('role')).toBe('slider')
    await wrapper.get('[data-testid="candidate-volume-a"]').setValue('0.4')
    expect(audio.volume).toBe(0.4)
    await wrapper.get('[data-testid="candidate-volume-b"]').setValue('0.9')
    expect(wrapper.get<HTMLInputElement>('[data-testid="candidate-volume-a"]').element.value).toBe('0.4')
    expect(wrapper.get<HTMLInputElement>('[data-testid="candidate-volume-b"]').element.value).toBe('0.9')
    wrapper.unmount()
  })

  it('renders generation details from the API instead of fixed demo copy', async () => {
    const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
      if (String(input).endsWith('/api/preferences')) {
        return new Response(JSON.stringify({ defaults: {}, style_markdown: '' }), { status: 200 })
      }
      if (String(input).endsWith('/api/preferences/defaults')) {
        return new Response(JSON.stringify({ language: 'zh', instrumental: false, vocal_gender: 'm', suno_model: 'V5' }), { status: 200 })
      }
      return new Response(JSON.stringify({
        request_id: 'real-result',
        user_request: '雨夜爵士，萨克斯与钢琴对话',
        status: 'completed',
        stage: 'completed',
        progress: 100,
        task_id: 'task_real_result_1234',
        settings: { language: 'zh', instrumental: false, vocal_gender: 'm', suno_model: 'V5' },
        stage_events: [],
        created_at: '2026-07-14T12:30:00',
        updated_at: '2026-07-14T12:40:00',
        candidates: [{
          audio_id: 'jazz', title: '雨夜对话', duration: 120,
          audio_url: '/api/audio/jazz', download_url: '/api/audio/jazz/download', cover_url: '/api/cover/jazz',
          model_name: 'chirp-v5', tags: 'jazz, warm', create_time: '2026-07-14T12:39:00',
        }],
      }), { status: 200 })
    })
    vi.stubGlobal('fetch', fetchMock)
    const pinia = createPinia(); const router = testRouter()
    await router.push('/generations/real-result/result'); await router.isReady()

    const wrapper = mount(ResultPage, { global: { plugins: [pinia, router] } })

    await vi.waitFor(() => expect(wrapper.get('[data-testid="result-request"]').text()).toContain('雨夜爵士'))
    expect(wrapper.get('[data-testid="result-model"]').text()).toBe('chirp-v5')
    expect(wrapper.get('[data-testid="result-completed-at"]').text()).toContain('2026')
    expect(wrapper.text()).toContain('jazz, warm')
    expect(wrapper.text()).not.toContain('中文 lo-fi pop · 温暖克制 · 女声 · 约 90 秒')
    await wrapper.get('.detail-card .button.full').trigger('click')
    const saveCall = fetchMock.mock.calls.find(([url]) => String(url).endsWith('/api/preferences/defaults'))
    expect(JSON.parse(String(saveCall?.[1]?.body))).toMatchObject({ vocal_gender: 'm', suno_model: 'V5' })
    wrapper.unmount()
  })

  it('does not activate result demo data without the explicit demo query', async () => {
    vi.stubGlobal('fetch', vi.fn(async (input: RequestInfo | URL) => {
      if (String(input).endsWith('/api/preferences')) {
        return new Response(JSON.stringify({ defaults: {}, style_markdown: '' }), { status: 200 })
      }
      return new Response(JSON.stringify({
        request_id: 'demo-a', user_request: '来自 API 的真实任务', status: 'completed', stage: 'completed', progress: 100,
        candidates: [], stage_events: [], created_at: '2026-07-14T12:00:00', updated_at: '2026-07-14T12:01:00',
      }), { status: 200 })
    }))
    const pinia = createPinia(); const router = testRouter()
    await router.push('/generations/demo-a/result'); await router.isReady()

    const wrapper = mount(ResultPage, { global: { plugins: [pinia, router] } })

    await vi.waitFor(() => expect(wrapper.get('[data-testid="result-request"]').text()).toContain('来自 API 的真实任务'))
    wrapper.unmount()
  })
})

describe('works empty state', () => {
  it('does not substitute demo works for an empty real API response', async () => {
    vi.stubGlobal('fetch', vi.fn(async () => new Response(JSON.stringify({ items: [] }), { status: 200 })))
    const pinia = createPinia(); const router = testRouter()
    await router.push('/works'); await router.isReady()
    const wrapper = mount(WorksPage, { global: { plugins: [pinia, router] } })
    await vi.waitFor(() => expect(wrapper.get('[data-testid="works-empty"]').text()).toContain('还没有作品'))
    expect(wrapper.findAll('.work-row')).toHaveLength(0)
  })

  it('does not show a demo cover or an inert more button for unfinished work', async () => {
    vi.stubGlobal('fetch', vi.fn(async () => new Response(JSON.stringify({ items: [{
      request_id: 'running-1', user_request: '真实任务', status: 'running', stage: 'lyrics', progress: 20,
      candidates: [], stage_events: [], created_at: '2026-07-14T12:00:00', updated_at: '2026-07-14T12:01:00',
    }] }), { status: 200 })))
    const pinia = createPinia(); const router = testRouter()
    await router.push('/works'); await router.isReady()

    const wrapper = mount(WorksPage, { global: { plugins: [pinia, router] } })

    await vi.waitFor(() => expect(wrapper.findAll('.work-row')).toHaveLength(1))
    expect(wrapper.find('.work-song img').exists()).toBe(false)
    expect(wrapper.find('.icon-button').exists()).toBe(false)
    wrapper.unmount()
  })

  it('gives every playable work control an accessible name', async () => {
    vi.stubGlobal('fetch', vi.fn(async () => new Response(JSON.stringify({ items: [] }), { status: 200 })))
    const pinia = createPinia(); const router = testRouter()
    await router.push('/works?demo=1'); await router.isReady()

    const wrapper = mount(WorksPage, { global: { plugins: [pinia, router] } })
    const playButtons = wrapper.findAll('.work-row button.round')

    expect(playButtons.length).toBeGreaterThan(0)
    expect(playButtons.every(button => Boolean(button.attributes('aria-label')))).toBe(true)
    wrapper.unmount()
  })

  it('opens the existing result page to choose a retained version and omits quick download', async () => {
    vi.stubGlobal('fetch', vi.fn(async () => new Response(JSON.stringify({ items: [] }), { status: 200 })))
    const pinia = createPinia(); const router = testRouter()
    await router.push('/works?demo=1'); await router.isReady()

    const wrapper = mount(WorksPage, { global: { plugins: [pinia, router] } })
    const first = wrapper.get('.work-row')
    const versionLink = first.get('[data-testid="view-versions"]')

    expect(versionLink.text()).toContain('查看 2 个版本')
    expect(versionLink.attributes('href')).toContain('/generations/demo-a/result')
    expect(first.find('a[download], a[href*="download"]').exists()).toBe(false)
    expect(first.get('.work-song-title').attributes('href')).toContain('/generations/demo-a/result')
  })

  it('confirms permanent task deletion and clears the active player after success', async () => {
    const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      if (init?.method === 'DELETE') return new Response(null, { status: 204 })
      return new Response(JSON.stringify({ items: [] }), { status: 200 })
    })
    vi.stubGlobal('fetch', fetchMock)
    const pinia = createPinia(); const router = testRouter()
    await router.push('/works?demo=1'); await router.isReady()
    setActivePinia(pinia)
    const player = usePlayerStore()
    player.select({ requestId: 'demo-a', audioId: 'a', title: 'A', subtitle: '', audioUrl: '/a', coverUrl: '/a.jpg' })
    const wrapper = mount(WorksPage, { global: { plugins: [pinia, router] } })

    await wrapper.get('[data-testid="delete-generation-demo-a"]').trigger('click')
    expect(wrapper.get('[role="dialog"]').text()).toContain('不可恢复')
    await wrapper.get('[data-testid="confirm-delete-generation"]').trigger('click')
    await vi.waitFor(() => expect(fetchMock).toHaveBeenCalledWith('/api/generations/demo-a', expect.objectContaining({ method: 'DELETE' })))
    await vi.waitFor(() => expect(player.current).toBeNull())
  })

  it('warns that stopped work will lose its remote resume task id', async () => {
    vi.stubGlobal('fetch', vi.fn(async () => new Response(JSON.stringify({ items: [{
      request_id: 'stopped-1', user_request: 'x', status: 'stopped', stage: 'stopped_waiting', progress: 60,
      task_id: 'remote-task', candidates: [], stage_events: [], created_at: '2026-07-14T12:00:00', updated_at: '2026-07-14T12:01:00',
    }] }), { status: 200 })))
    const pinia = createPinia(); const router = testRouter()
    await router.push('/works'); await router.isReady()
    const wrapper = mount(WorksPage, { global: { plugins: [pinia, router] } })
    await vi.waitFor(() => expect(wrapper.findAll('.work-row')).toHaveLength(1))

    await wrapper.get('[data-testid="delete-generation-stopped-1"]').trigger('click')

    expect(wrapper.get('[role="dialog"]').text()).toContain('不能再继续查询远程任务')
  })
})
