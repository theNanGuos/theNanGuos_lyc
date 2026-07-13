import { mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createMemoryHistory, createRouter } from 'vue-router'

import CreatePage from '../src/pages/CreatePage.vue'
import PreferencesPage from '../src/pages/PreferencesPage.vue'
import ResultPage from '../src/pages/ResultPage.vue'
import WorksPage from '../src/pages/WorksPage.vue'
import { usePreferencesStore } from '../src/stores/preferences'
import { useGenerationStore } from '../src/stores/generation'
import { demoGeneration } from '../src/data/demo'

const testRouter = () => createRouter({ history: createMemoryHistory(), routes: [
  { path: '/', component: { template: '<div />' } },
  { path: '/create', component: { template: '<div />' } },
  { path: '/works', component: { template: '<div />' } },
  { path: '/preferences', component: { template: '<div />' } },
  { path: '/generations/:id/result', component: { template: '<div />' } },
] })

describe('creation controls', () => {
  beforeEach(() => setActivePinia(createPinia()))

  it('keeps advanced Suno parameters collapsed until requested', async () => {
    const router = testRouter()
    const wrapper = mount(CreatePage, { global: { plugins: [createPinia(), router] } })
    expect(wrapper.find('[data-testid="advanced-fields"]').exists()).toBe(false)
    await wrapper.get('[data-testid="advanced-toggle"]').trigger('click')
    expect(wrapper.get('[data-testid="advanced-fields"]').text()).toContain('排除标签')
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
    await router.push('/generations/demo-a/result'); await router.isReady()
    setActivePinia(pinia)
    useGenerationStore().current = demoGeneration('demo-a') ?? null
    const wrapper = mount(ResultPage, { attachTo: document.body, global: { plugins: [pinia, router] } })
    await wrapper.get('[data-testid="candidate-play-a"]').trigger('click')
    const audio = wrapper.get('audio').element as HTMLAudioElement
    expect(audio.getAttribute('src')).toContain('/demo-a/a.mp3')
    await vi.waitFor(() => expect(HTMLMediaElement.prototype.play).toHaveBeenCalled())
    Object.defineProperty(audio, 'duration', { configurable: true, value: 92 })
    Object.defineProperty(audio, 'currentTime', { configurable: true, writable: true, value: 38 })
    await wrapper.get('audio').trigger('loadedmetadata'); await wrapper.get('audio').trigger('timeupdate')
    expect(wrapper.get('[data-testid="candidate-time-a"]').text()).toContain('0:38 / 1:32')
    await wrapper.get('[data-testid="candidate-volume"]').setValue('0.4')
    expect(audio.volume).toBe(0.4)
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
})
