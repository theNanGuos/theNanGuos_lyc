<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { AdjustmentsHorizontalIcon, ArrowUpIcon, BookmarkIcon, ChevronDownIcon, ChevronUpIcon, PencilIcon, SparklesIcon } from '@heroicons/vue/24/outline'
import AppShell from '../components/AppShell.vue'
import { buildGenerationPayload, useGenerationStore, type DefaultField } from '../stores/generation'
import { usePreferencesStore } from '../stores/preferences'

const router = useRouter(); const generation = useGenerationStore(); const preferences = usePreferencesStore()
const prompt = ref('一首适合深夜学习的中文 lo-fi pop，温暖、克制，女声，约 90 秒')
const advanced = ref(false); const saveDefaults = ref(false)
const settings = ref({ language: 'zh', instrumental: false, vocal_gender: 'f', suno_model: 'V5', title: '', negativeTags: '强烈失真, 重鼓点', styleWeight: 0.65, weirdnessConstraint: 0.35, audioWeight: 0.5 })
const plan = ref({ 风格: 'lo-fi pop', 情绪: '温暖、克制', 语言: '中文', 人声: '女声', 时长目标: '约 90 秒', 歌曲结构: '主歌 / 副歌 / 主歌 / 副歌', 避免: '强烈失真、重鼓点' })
const summary = computed(() => `中文 lo-fi pop，温暖克制，${settings.value.instrumental ? '纯音乐' : '女声'}，约 90 秒。`)
onMounted(async () => { try { await preferences.load(); Object.assign(settings.value, preferences.defaults) } catch { /* use system defaults */ } })
async function submit() {
  if (!prompt.value.trim()) return
  const savedFields: DefaultField[] = saveDefaults.value ? ['language', 'instrumental', 'vocal_gender', 'suno_model'] : []
  const result = await generation.create(buildGenerationPayload({ prompt: prompt.value, settings: settings.value, savedFields }))
  await router.push(`/generations/${result.request_id}`)
}
</script>

<template>
  <div class="create-layout"><AppShell><section class="create-content page-center">
    <header class="hero"><h1>和智能体一起写首歌</h1><p><SparklesIcon/>描述想法，智能体会先复述理解，再开始协作</p></header>
    <div class="prompt-box"><textarea v-model="prompt" maxlength="500" aria-label="自然语言创作描述"/><div class="prompt-tools"><span>{{ prompt.length }}/500</span><button class="round primary" aria-label="提交描述" @click="submit"><ArrowUpIcon/></button></div></div>
    <div class="understanding"><SparklesIcon/><strong>我理解为：</strong><span>{{ summary }}</span></div>
    <section class="plan-card"><div class="section-row"><h2>创作方案</h2><button class="link"><AdjustmentsHorizontalIcon/>调整方案</button></div>
      <div v-for="(value, key) in plan" :key="key" class="plan-row"><b>{{ key }}</b><span>{{ value }}</span><button aria-label="编辑"><PencilIcon/></button></div>
    </section>
    <div class="actions"><button class="button"><BookmarkIcon/>保存草稿</button><button class="button primary" :disabled="generation.loading" @click="submit"><SparklesIcon/>{{ generation.loading ? '正在提交…' : '提交生成' }}</button></div>
    <p v-if="generation.error" class="error-copy">{{ generation.error }}</p>
  </section></AppShell>
  <aside class="settings-panel"><div class="panel-title"><h2>本次生成设置</h2></div>
    <label>语言<select v-model="settings.language"><option value="zh">中文</option><option value="en">英文</option><option value="ja">日文</option></select></label>
    <fieldset><legend>是否纯音乐</legend><label class="radio"><input v-model="settings.instrumental" type="radio" :value="false"/>否（包含人声）</label><label class="radio"><input v-model="settings.instrumental" type="radio" :value="true"/>是（纯音乐）</label></fieldset>
    <label>人声<select v-model="settings.vocal_gender" :disabled="settings.instrumental"><option value="f">女声</option><option value="m">男声</option></select></label>
    <label>Suno 模型<select v-model="settings.suno_model"><option>V5</option><option>V4_5PLUS</option><option>V4_5</option><option>V4</option></select></label>
    <label>歌曲标题<input v-model="settings.title" placeholder="选填，留空将由智能体生成"/></label>
    <button data-testid="advanced-toggle" class="advanced-toggle" @click="advanced = !advanced"><span><b>高级 Suno 参数</b><small>排除标签、风格权重、创意程度、音频权重</small></span><ChevronUpIcon v-if="advanced"/><ChevronDownIcon v-else/></button>
    <div v-if="advanced" data-testid="advanced-fields" class="advanced-fields"><label>排除标签<input v-model="settings.negativeTags"/></label><label>风格权重 <output>{{ settings.styleWeight }}</output><input v-model.number="settings.styleWeight" type="range" min="0" max="1" step="0.05"/></label><label>创意程度 <output>{{ settings.weirdnessConstraint }}</output><input v-model.number="settings.weirdnessConstraint" type="range" min="0" max="1" step="0.05"/></label><label>音频权重 <output>{{ settings.audioWeight }}</output><input v-model.number="settings.audioWeight" type="range" min="0" max="1" step="0.05"/></label></div>
    <label class="check"><input v-model="saveDefaults" type="checkbox"/>将语言、人声和模型保存为默认偏好</label><small class="muted">仅影响下次默认值，本次输入始终优先</small>
    <RouterLink class="style-link" to="/preferences">编辑长期创作偏好（Markdown）</RouterLink>
  </aside></div>
</template>
