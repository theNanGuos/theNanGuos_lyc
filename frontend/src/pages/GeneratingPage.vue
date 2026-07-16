<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { CheckIcon, LockClosedIcon, SparklesIcon } from '@heroicons/vue/24/outline'
import AppShell from '../components/AppShell.vue'
import { estimatedGenerationProgress, generationStatusCopy, isTerminalGenerationStatus, normalizeGenerationStatus, useGenerationStore } from '../stores/generation'
import { demoGeneration, isDemoId } from '../data/demo'
import type { StageEvent } from '../api/client'

const route = useRoute(); const router = useRouter(); const store = useGenerationStore(); const id = String(route.params.id); const elapsed = ref(0); const stageElapsed = ref(0); let timer: number | undefined
const steps = ['理解创作需求', '生成歌词', '规划曲式与和弦', '设计编曲与风格', '提交 Suno 生成']
const stepStages = ['conductor', 'lyrics', 'music_planner', 'arrangement', 'suno_submit']
const remoteStages = new Set(['PENDING', 'TEXT_SUCCESS', 'FIRST_SUCCESS', 'SUCCESS', 'saving_media', 'completed'])
const normalizedStatus = computed(() => normalizeGenerationStatus(store.current?.status ?? 'queued'))
const activeStage = computed(() => generationStatusCopy(isTerminalGenerationStatus(store.current?.status ?? '') ? (store.current?.status ?? 'queued') : (store.current?.stage ?? 'queued')))
const remoteCopy = computed(() => store.current?.stage === 'FIRST_SUCCESS' || store.current?.status === 'FIRST_SUCCESS' ? '第一首已完成，等待全部结果' : activeStage.value)
const elapsedCopy = computed(() => `${Math.floor(elapsed.value / 60)} 分 ${(elapsed.value % 60).toString().padStart(2, '0')} 秒`)
const displayedProgress = computed(() => estimatedGenerationProgress(store.current?.stage ?? 'queued', store.current?.progress ?? 0, stageElapsed.value))
const currentStepIndex = computed(() => {
  const stage = store.current?.stage ?? 'queued'
  if (remoteStages.has(stage)) return steps.length
  return stepStages.indexOf(stage)
})
const stepState = (index: number) => index < currentStepIndex.value ? 'done' : index === currentStepIndex.value ? 'active' : 'pending'
const remoteStepState = computed(() => normalizedStatus.value === 'completed'
  ? 'done'
  : currentStepIndex.value >= steps.length ? 'active' : 'pending')
const stageEvents = computed(() => store.current?.stage_events ?? [])
const eventFor = (stages: string[]) => {
  const matches = stageEvents.value.filter(event => stages.includes(event.stage))
  return matches.at(-1)
}
const formatEventTime = (event?: StageEvent) => event
  ? new Date(event.at).toLocaleTimeString('zh-CN', { hour12: false })
  : '等待中'
const timeline = computed(() => [
  ...steps.map((label, index) => ({ label, event: eventFor([stepStages[index]]), active: currentStepIndex.value === index })),
  { label: '等待完整歌曲', event: eventFor([...remoteStages]), active: currentStepIndex.value >= steps.length },
])
watch(() => store.current?.stage, (stage, previous) => { if (stage !== previous) stageElapsed.value = 0 })
async function poll() {
  if (isDemoId(id) && route.query.demo === '1') { store.current = demoGeneration(id) ?? null; return }
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
  <p class="sr-only" role="status" aria-live="polite" aria-atomic="true">正在{{ activeStage }}</p>
  <div class="progress-ring" :style="{ '--progress': `${displayedProgress}%` }"><strong>{{ displayedProgress }}<small>%</small></strong><span>预计进度</span></div>
  <strong class="elapsed">已等待 {{ elapsedCopy }}</strong><p class="muted centered">百分比为阶段内预计值；Suno 状态是实际生成依据</p>
  <ol class="step-list">
    <li v-for="(step, index) in steps" :key="step" data-testid="generation-step" :class="stepState(index)">
      <span class="step-index">{{ index + 1 }}</span>
      <i class="step-marker"><CheckIcon v-if="stepState(index) === 'done'"/></i>
      <div class="step-copy"><b>{{ step }}</b><small>{{ stepState(index) === 'done' ? '已完成' : stepState(index) === 'active' ? '进行中' : '等待中' }}</small></div>
    </li>
    <li data-testid="generation-step" :class="remoteStepState">
      <span class="step-index">6</span>
      <i class="step-marker"><CheckIcon v-if="remoteStepState === 'done'"/></i>
      <div class="step-copy"><b>等待完整歌曲</b><em class="step-state-badge">{{ generationStatusCopy(normalizedStatus) }}</em><small>Suno 状态：{{ remoteCopy }}</small></div>
    </li>
  </ol>
  <div data-testid="current-request" class="current-brief"><SparklesIcon/><b>当前创作：</b>{{ store.current?.user_request || '正在读取创作描述…' }}</div>
  <p v-if="normalizedStatus === 'failed'" class="error-copy" role="alert">{{ store.current?.error?.message || '生成失败，请调整描述后重试。' }}</p>
  <div class="actions"><button v-if="normalizedStatus === 'generating'" class="button" @click="stopWaiting">停止等待</button><button v-else-if="normalizedStatus === 'stopped' || normalizedStatus === 'interrupted'" class="button primary" @click="resumePolling">继续查询</button><RouterLink v-else-if="normalizedStatus === 'failed'" class="button primary" to="/create">重新创作</RouterLink><RouterLink class="button link-button" to="/works">返回作品列表</RouterLink></div>
  <p class="footnote"><LockClosedIcon/>你可以离开此页面，当前服务器进程仍会继续；停止等待不会撤销 Suno 远程任务</p>
</section></AppShell>
<aside class="progress-panel"><h2>协作进度</h2><div class="timeline"><div v-for="item in timeline" :key="item.label"><i></i><small>{{ formatEventTime(item.event) }}</small><strong :class="{ blue: item.active }">{{ item.label }}</strong><span>{{ item.event ? generationStatusCopy(item.event.stage) : '尚未开始' }}</span></div></div></aside></div></template>
