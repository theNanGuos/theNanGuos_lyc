<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { ArrowDownTrayIcon, BookmarkIcon, PauseIcon, PlayIcon, SparklesIcon, SpeakerWaveIcon } from '@heroicons/vue/24/outline'
import AppShell from '../components/AppShell.vue'
import TrackProgress from '../components/TrackProgress.vue'
import { useGenerationStore } from '../stores/generation'
import { generationStatusCopy } from '../stores/generation'
import { usePlayerStore } from '../stores/player'
import { usePreferencesStore } from '../stores/preferences'
import { demoGeneration, isDemoId } from '../data/demo'
const route = useRoute(); const generation = useGenerationStore(); const player = usePlayerStore(); const preferences = usePreferencesStore(); const id = String(route.params.id)
const audio = ref<HTMLAudioElement | null>(null)
onMounted(() => {
  if (isDemoId(id) && route.query.demo === '1') generation.current = demoGeneration(id) ?? null
  else void generation.load(id)
  void preferences.load()
})
const candidates = computed(() => generation.current?.candidates ?? [])
const firstCandidate = computed(() => candidates.value[0])
const maskedTask = computed(() => { const value = generation.current?.task_id ?? ''; return value.length > 8 ? `${value.slice(0, 8)}****${value.slice(-4)}` : '—' })
const actualModel = computed(() => firstCandidate.value?.model_name || generation.current?.settings?.suno_model || '—')
const completedAt = computed(() => {
  const value = firstCandidate.value?.create_time || generation.current?.updated_at
  return value ? new Date(value).toLocaleString('zh-CN', { hour12: false }) : '—'
})
const settingSummary = computed(() => {
  const settings = generation.current?.settings
  if (!settings) return '未保存本次设置'
  const language = ({ zh: '中文', en: '英文', ja: '日文' } as Record<string, string>)[settings.language ?? ''] ?? settings.language
  const vocal = settings.instrumental ? '纯音乐' : settings.vocal_gender === 'm' ? '男声' : settings.vocal_gender === 'f' ? '女声' : '人声未指定'
  return [language, vocal, settings.suno_model].filter(Boolean).join(' · ')
})
const canSaveSettings = computed(() => Boolean(generation.current?.settings && Object.keys(generation.current.settings).length))
async function saveCurrentDefaults() {
  const settings = generation.current?.settings
  if (!settings) return
  Object.assign(preferences.defaults, settings)
  await preferences.saveDefaults()
}
function trackFor(item: (typeof candidates.value)[number]) { return { requestId: id, audioId: item.audio_id, title: item.title, subtitle: item.tags || generation.current?.user_request || '', audioUrl: item.audio_url, coverUrl: item.cover_url, downloadUrl: item.download_url } }
function play(item: (typeof candidates.value)[number]) { player.select(trackFor(item)) }
const time = (value: number) => `${Math.floor(value / 60)}:${Math.floor(value % 60).toString().padStart(2, '0')}`
const candidateTime = (audioId: string) => player.current?.audioId === audioId ? player.currentTime : 0
const candidateDuration = (item: (typeof candidates.value)[number]) => player.current?.audioId === item.audio_id && player.duration ? player.duration : item.duration || 0
async function seek(item: (typeof candidates.value)[number], seconds: number) { if (player.current?.audioId !== item.audio_id) player.select(trackFor(item)); await nextTick(); if (audio.value) audio.value.currentTime = seconds; player.currentTime = seconds }
function setVolume(item: (typeof candidates.value)[number], event: Event) { const value = Number((event.target as HTMLInputElement).value); player.setVolume(item.audio_id, value); if (audio.value && player.current?.audioId === item.audio_id) audio.value.volume = value }
watch(() => player.current?.audioUrl, async () => {
  await nextTick()
  if (!audio.value) return
  audio.value.load(); audio.value.volume = player.current ? player.volumeFor(player.current.audioId) : 0.75
  if (player.playing) await audio.value.play().catch(() => { player.playing = false })
})
watch(() => player.playing, (playing) => { if (!audio.value) return; if (playing) void audio.value.play().catch(() => { player.playing = false }); else audio.value.pause() })
onBeforeUnmount(() => audio.value?.pause())
</script>
<template><AppShell><section class="result-page"><header class="hero"><h1>歌曲已生成</h1><p><SparklesIcon/>为你生成了 {{ candidates.length }} 个候选版本，可以试听并下载</p></header>
  <audio v-if="player.current" ref="audio" :src="player.current.audioUrl" @timeupdate="player.currentTime = audio?.currentTime ?? 0" @loadedmetadata="player.duration = audio?.duration ?? 0" @ended="player.playing = false"/>
  <div class="result-grid"><div><div data-testid="result-request" class="current-brief"><SparklesIcon/>{{ generation.current?.user_request || '正在读取创作描述…' }}</div>
    <section class="songs-card"><article v-for="item in candidates" :key="item.audio_id" class="song-row"><img :src="item.cover_url" :alt="`${item.title}封面`"/><div class="song-body"><h2>{{ item.title }}</h2><p>{{ item.tags || generation.current?.user_request || '未提供风格标签' }} · {{ item.duration ? time(item.duration) : '—' }}</p><div class="song-player"><button :data-testid="`candidate-play-${item.audio_id}`" class="round" :class="{ primary: player.current?.audioId === item.audio_id && player.playing }" :aria-label="player.current?.audioId === item.audio_id && player.playing ? `暂停 ${item.title}` : `播放 ${item.title}`" @click="play(item)"><PauseIcon v-if="player.current?.audioId === item.audio_id && player.playing"/><PlayIcon v-else/></button><TrackProgress :current-time="candidateTime(item.audio_id)" :duration="candidateDuration(item)" :label="`${item.title} 播放进度`" :test-id="`candidate-progress-${item.audio_id}`" @seek="seek(item, $event)"/></div><div class="song-tools"><span :data-testid="`candidate-time-${item.audio_id}`">{{ player.current?.audioId === item.audio_id ? time(player.currentTime) : '0:00' }} / {{ candidateDuration(item) ? time(candidateDuration(item)) : '—' }}</span><SpeakerWaveIcon/><input :value="player.volumeFor(item.audio_id)" :data-testid="`candidate-volume-${item.audio_id}`" type="range" min="0" max="1" step="0.05" :aria-label="`${item.title} 音量`" @input="setVolume(item, $event)"/><a class="button primary compact" :href="item.download_url"><ArrowDownTrayIcon/>下载 MP3</a></div></div></article>
    <div v-if="!candidates.length" class="empty-state">结果文件正在建立本地索引，请稍后刷新。</div></section>
    <div class="actions"><RouterLink class="button primary" to="/create"><SparklesIcon/>再创作一首</RouterLink><RouterLink class="button" to="/works">返回作品列表</RouterLink></div>
  </div><aside class="details-column"><section class="detail-card"><h2>生成详情</h2><dl><div><dt>状态</dt><dd><span class="badge success">{{ generationStatusCopy(generation.current?.status || 'completed') }}</span></dd></div><div><dt>模型</dt><dd data-testid="result-model">{{ actualModel }}</dd></div><div><dt>完成时间</dt><dd data-testid="result-completed-at">{{ completedAt }}</dd></div><div><dt>任务 ID</dt><dd>{{ maskedTask }}</dd></div></dl></section>
    <section class="detail-card"><h2><BookmarkIcon/>保存为默认偏好（可选）</h2><div class="preference-summary">{{ settingSummary }}</div><p>只保存你确认的设置，不保存本次标题与歌词</p><button class="button full" :disabled="!canSaveSettings" @click="saveCurrentDefaults">保存为默认偏好</button></section>
  </aside></div>
</section></AppShell></template>
