<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { CheckCircleIcon, ShieldCheckIcon, SparklesIcon } from '@heroicons/vue/24/outline'
import { marked } from 'marked'
import AppShell from '../components/AppShell.vue'; import { usePreferencesStore } from '../stores/preferences'
const preferences = usePreferencesStore(); const tab = ref<'edit'|'preview'>('edit'); const confirmClear = ref(false); const notice = ref('')
const escapedMarkdown = computed(() => preferences.markdown.replaceAll('&', '&amp;').replaceAll('<', '&lt;').replaceAll('>', '&gt;'))
const preview = computed(() => marked.parse(escapedMarkdown.value, { async: false }))
onMounted(() => { void preferences.load().catch(() => undefined) })
async function saveDefaults(){ await preferences.saveDefaults(); notice.value='默认设置已保存' }
async function saveStyle(){ await preferences.saveStyle(); notice.value='长期创作偏好已保存' }
async function clearAll(){ await preferences.clear(); confirmClear.value=false; notice.value='偏好已清除，作品未受影响' }
</script>
<template><AppShell><section class="preferences-page"><header class="page-heading"><h1>偏好设置</h1><p><SparklesIcon/>管理下次创作时使用的默认值和长期创作倾向</p></header>
  <section class="default-settings"><h2>默认生成设置</h2><p>这些设置会作为下次创作的初始值，你的当次描述始终优先</p><div class="settings-grid"><label>默认语言<select v-model="preferences.defaults.language"><option value="zh">中文</option><option value="en">英文</option><option value="ja">日文</option></select></label><label>默认是否纯音乐<select v-model="preferences.defaults.instrumental"><option :value="false">否（包含人声）</option><option :value="true">是（纯音乐）</option></select></label><label>默认人声<select v-model="preferences.defaults.vocal_gender"><option value="f">女声</option><option value="m">男声</option><option :value="null">不限</option></select></label><label>默认 Suno 模型<select v-model="preferences.defaults.suno_model"><option>V5</option><option>V4_5PLUS</option><option>V4_5</option><option>V4</option></select></label></div><div class="settings-actions"><p><ShieldCheckIcon/><b>已确认的偏好</b><span>保存在结构化偏好中</span></p><button class="button primary" @click="saveDefaults"><SparklesIcon/>保存默认设置</button><button class="button" @click="preferences.restoreSystemDefaults">恢复系统默认值</button></div></section>
  <section class="style-settings"><h2>长期创作偏好</h2><p>使用 Markdown 描述长期稳定的风格、编曲和避免项，智能体会将它作为创作参考</p><div class="editor"><div class="editor-tabs"><button :class="{active:tab==='edit'}" @click="tab='edit'">编辑</button><button :class="{active:tab==='preview'}" @click="tab='preview'">预览</button></div><textarea v-if="tab==='edit'" v-model="preferences.markdown" spellcheck="false" placeholder="# 长期创作偏好&#10;&#10;## 整体倾向&#10;偏好温暖、克制、有空间感的音乐。"/><div v-else class="markdown-preview" v-html="preview"/></div><div class="save-line"><p><CheckCircleIcon/>{{ notice || '仅保存你主动确认的内容，不会根据单次创作自动修改' }}</p><button class="button primary" @click="saveStyle"><SparklesIcon/>保存创作偏好</button></div></section>
  <section class="danger-zone"><div><h3>清除长期偏好</h3><p>删除默认设置和创作偏好，不影响已生成作品</p></div><button data-testid="clear-preferences" class="button danger" @click="confirmClear=true">清除偏好</button></section>
  <div v-if="confirmClear" class="modal-backdrop"><section role="dialog" aria-modal="true" class="confirm-dialog"><h2>确定清除全部偏好？</h2><p>默认生成设置和长期创作偏好将被清除，但不会删除已生成作品。</p><div class="actions"><button data-testid="cancel-clear" class="button" @click="confirmClear=false">取消</button><button class="button danger solid" @click="clearAll">确认清除</button></div></section></div>
</section></AppShell></template>
