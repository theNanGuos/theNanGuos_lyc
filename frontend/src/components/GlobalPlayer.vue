<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, ref, watch } from 'vue'
import { ArrowDownTrayIcon, PauseIcon, PlayIcon, SpeakerWaveIcon } from '@heroicons/vue/24/solid'
import { usePlayerStore } from '../stores/player'
import Waveform from './Waveform.vue'

const player = usePlayerStore()
const audio = ref<HTMLAudioElement | null>(null)
const percentage = computed(() => player.duration ? player.currentTime / player.duration * 100 : 0)
const time = (value: number) => `${Math.floor(value / 60)}:${Math.floor(value % 60).toString().padStart(2, '0')}`
watch(() => player.current?.audioUrl, async () => { await nextTick(); if (audio.value) { audio.value.load(); audio.value.volume = player.volume } })
watch(() => player.playing, (playing) => { if (!audio.value) return; if (playing) void audio.value.play().catch(() => { player.playing = false }); else audio.value.pause() })
onBeforeUnmount(() => audio.value?.pause())
</script>
<template>
  <div v-if="player.current" class="global-player">
    <audio ref="audio" :src="player.current.audioUrl" @timeupdate="player.currentTime = audio?.currentTime ?? 0" @loadedmetadata="player.duration = audio?.duration ?? 0" @ended="player.playing = false" />
    <img :src="player.current.coverUrl" :alt="`${player.current.title}封面`" />
    <div class="track-copy"><strong>{{ player.current.title }}</strong><span>{{ player.current.subtitle }}</span></div>
    <button class="round primary" :aria-label="player.playing ? '暂停' : '播放'" @click="player.toggle"><PauseIcon v-if="player.playing"/><PlayIcon v-else/></button>
    <div class="player-progress"><Waveform :progress="percentage"/><span>{{ time(player.currentTime) }} / {{ time(player.duration) }}</span></div>
    <SpeakerWaveIcon class="small-icon"/><input v-model.number="player.volume" class="volume" type="range" min="0" max="1" step="0.05" @input="audio && (audio.volume = player.volume)" />
    <a v-if="player.current.downloadUrl" class="button primary" :href="player.current.downloadUrl"><ArrowDownTrayIcon />下载 MP3</a>
  </div>
</template>
