<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { ArrowPathIcon, ArrowUpIcon, ChevronDownIcon, ChevronUpIcon, SparklesIcon } from '@heroicons/vue/24/outline'
import AppShell from '../components/AppShell.vue'
import { buildGenerationPayload, useGenerationStore, type DefaultField } from '../stores/generation'
import { usePreferencesStore } from '../stores/preferences'

const router = useRouter(); const generation = useGenerationStore(); const preferences = usePreferencesStore()
const prompt = ref('')
const advanced = ref(false); const saveDefaults = ref(false)
const settings = ref({ language: 'zh', instrumental: false, vocal_gender: 'f', suno_model: 'V5', title: '', retentionLimit: 1 as 1 | 2 | null, negativeTags: '强烈失真, 重鼓点', styleWeight: 0.65, weirdnessConstraint: 0.35, audioWeight: 0.5 })
const preview = computed(() => generation.currentPreview)
const summary = computed(() => {
  const spec = preview.value?.song_spec
  if (!spec) return '提交描述后，Conductor 会先生成可编辑的创作方案。'
  const vocal = spec.vocal.enabled ? (spec.vocal.gender === 'male' ? '男声' : spec.vocal.gender === 'female' ? '女声' : '人声') : '纯音乐'
  return `${spec.language} · ${spec.genre} · ${spec.mood.join('、')} · ${vocal} · 约 ${spec.duration_seconds} 秒`
})
const moodText = computed({
  get: () => preview.value?.song_spec.mood.join('、') ?? '',
  set: value => { if (preview.value) preview.value.song_spec.mood = value.split(/[、,，]/).map(item => item.trim()).filter(Boolean) },
})
const structureText = computed({
  get: () => preview.value?.song_spec.structure.join(' / ') ?? '',
  set: value => { if (preview.value) preview.value.song_spec.structure = value.split('/').map(item => item.trim()).filter(Boolean) },
})
const avoidText = computed({
  get: () => preview.value?.song_spec.constraints.avoid.join('、') ?? '',
  set: value => { if (preview.value) preview.value.song_spec.constraints.avoid = value.split(/[、,，]/).map(item => item.trim()).filter(Boolean) },
})
onMounted(async () => {
  generation.clearPreview()
  try { await preferences.load(); Object.assign(settings.value, preferences.defaults) } catch { /* use system defaults */ }
})
watch(prompt, value => { if (generation.currentPreview && value !== generation.previewPrompt) generation.clearPreview() })
async function requestPreview() {
  if (!prompt.value.trim()) return
  const payload = buildGenerationPayload({ prompt: prompt.value, settings: settings.value, savedFields: [] })
  const result = await generation.loadPreview({ prompt: payload.prompt, overrides: payload.overrides })
  settings.value.title = result.song_spec.title
  settings.value.language = result.song_spec.language
  settings.value.instrumental = !result.song_spec.vocal.enabled
  if (result.song_spec.vocal.gender) settings.value.vocal_gender = result.song_spec.vocal.gender === 'male' ? 'm' : 'f'
  settings.value.negativeTags = result.song_spec.constraints.avoid.join(', ')
}
async function submit() {
  if (!prompt.value.trim()) return
  if (!preview.value) { await requestPreview(); return }
  const savedFields: DefaultField[] = saveDefaults.value ? ['language', 'instrumental', 'vocal_gender', 'suno_model'] : []
  const spec = preview.value.song_spec
  const approvedSongSpec = {
    ...spec,
    title: settings.value.title.trim() || spec.title,
    language: settings.value.language,
    vocal: {
      ...spec.vocal,
      enabled: !settings.value.instrumental,
      gender: settings.value.instrumental ? null : settings.value.vocal_gender === 'm' ? 'male' as const : 'female' as const,
    },
    constraints: { ...spec.constraints, avoid: avoidText.value.split(/[、,，]/).map(item => item.trim()).filter(Boolean) },
  }
  const result = await generation.create({
    ...buildGenerationPayload({ prompt: prompt.value, settings: settings.value, savedFields }),
    preview_id: preview.value.preview_id,
    approved_song_spec: approvedSongSpec,
  })
  await router.push(`/generations/${result.request_id}`)
}
</script>

<template>
  <div class="create-layout"><AppShell><section class="create-content page-center">
    <header class="hero"><h1>和智能体一起写首歌</h1><p><SparklesIcon/>描述想法，智能体会先复述理解，再开始协作</p></header>
    <div class="prompt-box"><textarea v-model="prompt" maxlength="500" aria-label="自然语言创作描述" placeholder="例如：一首适合深夜学习的中文 lo-fi pop，温暖、克制，女声，约 90 秒"/><div class="prompt-tools"><span>{{ prompt.length }}/500</span><button class="round primary" aria-label="提交描述" :disabled="generation.previewLoading" @click="requestPreview"><ArrowUpIcon/></button></div></div>
    <div class="understanding"><SparklesIcon/><strong>我理解为：</strong><span>{{ summary }}</span></div>
    <section class="plan-card"><div class="section-row"><h2>创作方案</h2><button v-if="preview" class="link" :disabled="generation.previewLoading" @click="requestPreview"><span data-testid="retry-preview-icon" data-icon="arrow-path"><ArrowPathIcon/></span>重新生成方案</button></div>
      <template v-if="preview">
        <div class="plan-row"><b>风格</b><input v-model="preview.song_spec.genre" data-testid="plan-genre" aria-label="风格"/></div>
        <div class="plan-row"><b>情绪</b><input v-model="moodText" aria-label="情绪"/></div>
        <div class="plan-row"><b>语言</b><input v-model="preview.song_spec.language" aria-label="方案语言"/></div>
        <div class="plan-row"><b>人声</b><span>{{ preview.song_spec.vocal.enabled ? (preview.song_spec.vocal.gender === 'male' ? '男声' : preview.song_spec.vocal.gender === 'female' ? '女声' : '未指定') : '纯音乐' }}</span></div>
        <div class="plan-row"><b>时长目标</b><input v-model.number="preview.song_spec.duration_seconds" data-testid="plan-duration" type="number" min="30" max="600" aria-label="时长秒数"/></div>
        <div class="plan-row"><b>歌曲结构</b><input v-model="structureText" aria-label="歌曲结构"/></div>
        <div class="plan-row"><b>避免</b><input v-model="avoidText" aria-label="避免项"/></div>
      </template>
      <p v-else class="empty-state">{{ generation.previewLoading ? 'Conductor 正在理解描述并生成方案…' : '提交上方描述后，这里会显示可编辑方案。' }}</p>
    </section>
    <div class="actions"><button data-testid="confirm-generation" class="button primary" :disabled="generation.loading || generation.previewLoading" @click="submit"><SparklesIcon/>{{ generation.loading ? '正在提交…' : preview ? '确认方案并生成' : '先生成创作方案' }}</button></div>
    <p v-if="generation.error" class="error-copy">{{ generation.error }}</p>
  </section></AppShell>
  <aside class="settings-panel"><div class="panel-title"><h2>本次生成设置</h2></div>
    <label>语言<select v-model="settings.language"><option value="zh">中文</option><option value="en">英文</option><option value="ja">日文</option></select></label>
    <fieldset><legend>是否纯音乐</legend><label class="radio"><input v-model="settings.instrumental" type="radio" :value="false"/>否（包含人声）</label><label class="radio"><input v-model="settings.instrumental" type="radio" :value="true"/>是（纯音乐）</label></fieldset>
    <label>人声<select v-model="settings.vocal_gender" :disabled="settings.instrumental"><option value="f">女声</option><option value="m">男声</option></select></label>
    <label>Suno 模型<select v-model="settings.suno_model"><option>V5</option><option>V4_5PLUS</option><option>V4_5</option><option>V4</option></select></label>
    <label>本地保留数量<select v-model="settings.retentionLimit" aria-label="本地保留数量"><option :value="1">1 首</option><option :value="2">2 首</option><option :value="null">全部</option></select><small data-testid="retention-help" class="muted retention-help">仅控制本地保存，不会减少供应商实际生成数量或费用。</small></label>
    <label>歌曲标题<input v-model="settings.title" placeholder="选填，留空将由智能体生成"/></label>
    <button data-testid="advanced-toggle" class="advanced-toggle" @click="advanced = !advanced"><span><b>高级 Suno 参数</b><small>排除标签、风格权重、创意程度、音频权重</small></span><ChevronUpIcon v-if="advanced"/><ChevronDownIcon v-else/></button>
    <div v-if="advanced" data-testid="advanced-fields" class="advanced-fields"><label>排除标签<input v-model="settings.negativeTags"/></label><label>风格权重 <output>{{ settings.styleWeight }}</output><input v-model.number="settings.styleWeight" type="range" min="0" max="1" step="0.05"/></label><label>创意程度 <output>{{ settings.weirdnessConstraint }}</output><input v-model.number="settings.weirdnessConstraint" type="range" min="0" max="1" step="0.05"/></label><label>音频权重 <output>{{ settings.audioWeight }}</output><input v-model.number="settings.audioWeight" type="range" min="0" max="1" step="0.05"/></label></div>
    <label class="check"><input v-model="saveDefaults" type="checkbox"/>将语言、人声和模型保存为默认偏好</label><small class="muted">仅影响下次默认值，本次输入始终优先</small>
    <RouterLink class="style-link" to="/preferences">编辑长期创作偏好（Markdown）</RouterLink>
  </aside></div>
</template>
