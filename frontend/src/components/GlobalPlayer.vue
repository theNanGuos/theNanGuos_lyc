<script setup lang="ts">
import { nextTick, onBeforeUnmount, ref, watch } from 'vue'
import { ArrowDownTrayIcon, PauseIcon, PlayIcon, SpeakerWaveIcon } from '@heroicons/vue/24/solid'
import { usePlayerStore } from '../stores/player'
import TrackProgress from './TrackProgress.vue'

const player = usePlayerStore()
const audio = ref<HTMLAudioElement | null>(null)
const time = (value: number) => `${Math.floor(value / 60)}:${Math.floor(value % 60).toString().padStart(2, '0')}`
watch(() => player.current?.audioUrl, async () => { await nextTick(); if (audio.value && player.current) { audio.value.load(); audio.value.volume = player.volumeFor(player.current.audioId) } })
watch(() => player.playing, (playing) => { if (!audio.value) return; if (playing) void audio.value.play().catch(() => { player.playing = false }); else audio.value.pause() })
function seek(seconds: number) { if (audio.value) audio.value.currentTime = seconds; player.currentTime = seconds }
function setVolume(event: Event) { if (!player.current) return; const value = Number((event.target as HTMLInputElement).value); player.setVolume(player.current.audioId, value); if (audio.value) audio.value.volume = value }
onBeforeUnmount(() => audio.value?.pause())
</script>
<template>
  <div v-if="player.current" class="global-player">
    <audio ref="audio" :src="player.current.audioUrl" @timeupdate="player.currentTime = audio?.currentTime ?? 0" @loadedmetadata="player.duration = audio?.duration ?? 0" @ended="player.playing = false" />
    <img :src="player.current.coverUrl" :alt="`${player.current.title}封面`" />
    <div class="track-copy"><strong>{{ player.current.title }}</strong><span>{{ player.current.subtitle }}</span></div>
    <button class="round primary" :aria-label="player.playing ? '暂停' : '播放'" @click="player.toggle"><PauseIcon v-if="player.playing"/><PlayIcon v-else/></button>
    <div class="player-progress"><TrackProgress :current-time="player.currentTime" :duration="player.duration" :label="`${player.current.title} 播放进度`" @seek="seek"/><span>{{ time(player.currentTime) }} / {{ time(player.duration) }}</span></div>
    <SpeakerWaveIcon class="small-icon"/><input :value="player.volumeFor(player.current.audioId)" class="volume" type="range" min="0" max="1" step="0.05" :aria-label="`${player.current.title} 音量`" @input="setVolume" />
    <a v-if="player.current.downloadUrl" class="button primary" :href="player.current.downloadUrl"><ArrowDownTrayIcon />下载 MP3</a>
  </div>
</template>
