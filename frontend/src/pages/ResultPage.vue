<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { ArrowDownTrayIcon, BookmarkIcon, PauseIcon, PlayIcon, SparklesIcon, SpeakerWaveIcon } from '@heroicons/vue/24/outline'
import AppShell from '../components/AppShell.vue'
import Waveform from '../components/Waveform.vue'
import { useGenerationStore } from '../stores/generation'
import { usePlayerStore } from '../stores/player'
import { usePreferencesStore } from '../stores/preferences'
import { demoGeneration, isDemoId } from '../data/demo'
const route = useRoute(); const generation = useGenerationStore(); const player = usePlayerStore(); const preferences = usePreferencesStore(); const id = String(route.params.id)
const audio = ref<HTMLAudioElement | null>(null)
onMounted(() => {
  if (isDemoId(id)) generation.current = demoGeneration(id) ?? null
  else void generation.load(id)
  void preferences.load()
})
const candidates = computed(() => generation.current?.candidates ?? [])
const maskedTask = computed(() => { const value = generation.current?.task_id ?? ''; return value.length > 8 ? `${value.slice(0, 8)}****${value.slice(-4)}` : '—' })
function play(item: (typeof candidates.value)[number]) { player.select({ requestId: id, audioId: item.audio_id, title: item.title, subtitle: 'lo-fi pop · 女声', audioUrl: item.audio_url, coverUrl: item.cover_url, downloadUrl: item.download_url }) }
const time = (value: number) => `${Math.floor(value / 60)}:${Math.floor(value % 60).toString().padStart(2, '0')}`
const progress = (audioId: string) => player.current?.audioId === audioId && player.duration ? player.currentTime / player.duration * 100 : 0
watch(() => player.current?.audioUrl, async () => {
  await nextTick()
  if (!audio.value) return
  audio.value.load(); audio.value.volume = player.volume
  if (player.playing) await audio.value.play().catch(() => { player.playing = false })
})
watch(() => player.playing, (playing) => { if (!audio.value) return; if (playing) void audio.value.play().catch(() => { player.playing = false }); else audio.value.pause() })
onBeforeUnmount(() => audio.value?.pause())
</script>
<template><AppShell><section class="result-page"><header class="hero"><h1>歌曲已生成</h1><p><SparklesIcon/>为你生成了 {{ candidates.length || 2 }} 个候选版本，可以试听并下载</p></header>
  <audio v-if="player.current" ref="audio" :src="player.current.audioUrl" @timeupdate="player.currentTime = audio?.currentTime ?? 0" @loadedmetadata="player.duration = audio?.duration ?? 0" @ended="player.playing = false"/>
  <div class="result-grid"><div><div class="current-brief"><SparklesIcon/>中文 lo-fi pop · 温暖克制 · 女声 · 约 90 秒</div>
    <section class="songs-card"><article v-for="item in candidates" :key="item.audio_id" class="song-row"><img :src="item.cover_url" :alt="`${item.title}封面`"/><div class="song-body"><h2>{{ item.title }}</h2><p>lo-fi pop · 女声 · {{ item.duration ? time(item.duration) : '—' }}</p><div class="song-player"><button :data-testid="`candidate-play-${item.audio_id}`" class="round" :class="{ primary: player.current?.audioId === item.audio_id && player.playing }" @click="play(item)"><PauseIcon v-if="player.current?.audioId === item.audio_id && player.playing"/><PlayIcon v-else/></button><Waveform :progress="progress(item.audio_id)"/></div><div class="song-tools"><span :data-testid="`candidate-time-${item.audio_id}`">{{ player.current?.audioId === item.audio_id ? time(player.currentTime) : '0:00' }} / {{ player.current?.audioId === item.audio_id && player.duration ? time(player.duration) : (item.duration ? time(item.duration) : '—') }}</span><SpeakerWaveIcon/><input v-model.number="player.volume" data-testid="candidate-volume" type="range" min="0" max="1" step="0.05" @input="audio && (audio.volume = player.volume)"/><a class="button primary compact" :href="item.download_url"><ArrowDownTrayIcon/>下载 MP3</a></div></div></article>
    <div v-if="!candidates.length" class="empty-state">结果文件正在建立本地索引，请稍后刷新。</div></section>
    <div class="actions"><RouterLink class="button primary" to="/create"><SparklesIcon/>再创作一首</RouterLink><RouterLink class="button" to="/works">返回作品列表</RouterLink></div>
  </div><aside class="details-column"><section class="detail-card"><h2>生成详情</h2><dl><div><dt>状态</dt><dd><span class="badge success">SUCCESS</span></dd></div><div><dt>模型</dt><dd>V5</dd></div><div><dt>完成时间</dt><dd>刚刚</dd></div><div><dt>任务 ID</dt><dd>{{ maskedTask }}</dd></div></dl><button class="link">查看创作方案</button></section>
    <section class="detail-card"><h2><BookmarkIcon/>保存为默认偏好（可选）</h2><div class="preference-summary">中文 · 女声 · V5</div><p>只保存你确认的设置，不保存本次标题与歌词</p><button class="button full" @click="preferences.saveDefaults">保存为默认偏好</button></section>
  </aside></div>
</section></AppShell></template>
