import { mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, it } from 'vitest'

import TrackProgress from '../src/components/TrackProgress.vue'
import { usePlayerStore } from '../src/stores/player'

describe('track progress', () => {
  it('uses real playback time and emits an accessible seek target', async () => {
    const wrapper = mount(TrackProgress, { props: { currentTime: 30, duration: 120, label: '晨曦微光 播放进度' } })
    const slider = wrapper.get('input[type="range"]')

    expect(slider.attributes('aria-label')).toBe('晨曦微光 播放进度')
    expect(slider.element).toHaveProperty('value', '30')
    expect(slider.attributes('max')).toBe('120')
    await slider.setValue('75')
    expect(wrapper.emitted('seek')?.[0]).toEqual([75])
  })
})

describe('per-candidate volume', () => {
  beforeEach(() => setActivePinia(createPinia()))

  it('keeps volume independent for each audio id', () => {
    const player = usePlayerStore()
    player.setVolume('first', 0.25)
    player.setVolume('second', 0.9)

    expect(player.volumeFor('first')).toBe(0.25)
    expect(player.volumeFor('second')).toBe(0.9)
    expect(player.volumeFor('new')).toBe(0.75)
  })
})
