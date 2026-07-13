<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { CheckIcon, LockClosedIcon, SparklesIcon } from '@heroicons/vue/24/outline'
import AppShell from '../components/AppShell.vue'
import Waveform from '../components/Waveform.vue'
import { estimatedGenerationProgress, generationStatusCopy, isTerminalGenerationStatus, normalizeGenerationStatus, useGenerationStore } from '../stores/generation'
import { demoGeneration, isDemoId } from '../data/demo'

const route = useRoute(); const router = useRouter(); const store = useGenerationStore(); const id = String(route.params.id); const elapsed = ref(0); const stageElapsed = ref(0); let timer: number | undefined
const steps = ['理解创作需求', '生成歌词', '规划曲式与和弦', '设计编曲与风格', '提交 Suno 生成']
const normalizedStatus = computed(() => normalizeGenerationStatus(store.current?.status ?? 'queued'))
const activeStage = computed(() => generationStatusCopy(isTerminalGenerationStatus(store.current?.status ?? '') ? (store.current?.status ?? 'queued') : (store.current?.stage ?? 'queued')))
const remoteCopy = computed(() => store.current?.stage === 'FIRST_SUCCESS' || store.current?.status === 'FIRST_SUCCESS' ? '第一首已完成，等待全部结果' : activeStage.value)
const elapsedCopy = computed(() => `${Math.floor(elapsed.value / 60)} 分 ${(elapsed.value % 60).toString().padStart(2, '0')} 秒`)
const displayedProgress = computed(() => estimatedGenerationProgress(store.current?.stage ?? 'queued', store.current?.progress ?? 0, stageElapsed.value))
watch(() => store.current?.stage, (stage, previous) => { if (stage !== previous) stageElapsed.value = 0 })
async function poll() {
  if (isDemoId(id)) { store.current = demoGeneration(id) ?? null; return }
  try {
    const value = await store.load(id)
    if (value.status === 'completed') await router.replace(`/generations/${id}/result`)
    if (isTerminalGenerationStatus(value.status) && timer !== undefined) { clearInterval(timer); timer = undefined }
  }
  catch (error) { store.error = error instanceof Error ? error.message : '状态加载失败' }
}
async function stopWaiting() { await store.stop(id); if (timer !== undefined) { clearInterval(timer); timer = undefined } }
function tick() { elapsed.value++; stageElapsed.value++; if (elapsed.value % 4 === 0) void poll() }
async function resumePolling() { await store.resume(id); if (timer === undefined) timer = window.setInterval(tick, 1000) }
onMounted(async () => {
  await poll()
  if (!isTerminalGenerationStatus(store.current?.status ?? '')) timer = window.setInterval(tick, 1000)
})
onBeforeUnmount(() => { if (timer !== undefined) clearInterval(timer) })
</script>
<template><div class="generating-layout"><AppShell><section class="generation-main">
  <header class="hero"><h1>正在为你创作</h1><p><SparklesIcon/>多智能体正在协作完成歌词、音乐规划与编曲设计</p></header>
  <div class="progress-ring" :style="{ '--progress': `${displayedProgress}%` }"><strong>{{ displayedProgress }}<small>%</small></strong><span>预计进度</span></div>
  <Waveform :progress="displayedProgress"/><strong class="elapsed">已等待 {{ elapsedCopy }}</strong><p class="muted centered">百分比为阶段内预计值；Suno 状态是实际生成依据</p>
  <ol class="step-list"><li v-for="(step, index) in steps" :key="step" class="done"><span>{{ index + 1 }}</span><i><CheckIcon/></i><div><b>{{ step }}</b><small>已完成</small></div></li><li :class="{ active: normalizedStatus === 'generating' }"><i></i><div><b>等待完整歌曲</b><em>{{ generationStatusCopy(normalizedStatus) }}</em><small>Suno 状态：{{ remoteCopy }}</small></div></li></ol>
  <div class="current-brief"><SparklesIcon/><b>当前创作：</b>中文 lo-fi pop · 温暖克制 · 女声 · 约 90 秒</div>
  <p v-if="normalizedStatus === 'failed'" class="error-copy" role="alert">{{ store.current?.error?.message || '生成失败，请调整描述后重试。' }}</p>
  <div class="actions"><button v-if="normalizedStatus === 'generating'" class="button" @click="stopWaiting">停止等待</button><button v-else-if="normalizedStatus === 'stopped' || normalizedStatus === 'interrupted'" class="button primary" @click="resumePolling">继续查询</button><RouterLink v-else-if="normalizedStatus === 'failed'" class="button primary" to="/create">重新创作</RouterLink><RouterLink class="button link-button" to="/works">返回作品列表</RouterLink></div>
  <p class="footnote"><LockClosedIcon/>你可以离开此页面，当前服务器进程仍会继续；停止等待不会撤销 Suno 远程任务</p>
</section></AppShell>
<aside class="progress-panel"><h2>协作进度</h2><div class="timeline"><div v-for="(step, index) in [...steps, '等待完整歌曲']" :key="step"><i></i><small>10:{{ 28 + index }}:{{ (41 + index * 11) % 60 }}</small><strong :class="{ blue: index === 5 }">{{ step }}</strong><span>{{ index === 5 ? remoteCopy : '已完成当前协作阶段' }}</span></div></div></aside></div></template>
