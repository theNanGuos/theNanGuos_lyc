<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { ArrowDownTrayIcon, EllipsisVerticalIcon, MagnifyingGlassIcon, MusicalNoteIcon, PlayIcon, SparklesIcon } from '@heroicons/vue/24/outline'
import AppShell from '../components/AppShell.vue'; import GlobalPlayer from '../components/GlobalPlayer.vue'
import type { Generation } from '../api/client'; import { generationStatusCopy, normalizeGenerationStatus, useGenerationStore } from '../stores/generation'; import { usePlayerStore } from '../stores/player'
import { demoGenerations, sortGenerations } from '../data/demo'
const store = useGenerationStore(); const player = usePlayerStore(); const route = useRoute(); const search = ref(''); const status = ref(''); const sort = ref<'newest'|'oldest'>('newest')
const rows = computed(() => {
  const base = route.query.demo === '1' ? demoGenerations() : store.items
  const filtered = base.filter(item => (!status.value || normalizeGenerationStatus(item.status) === status.value) && (!search.value || `${item.user_request} ${item.candidates.map(c=>c.title).join(' ')}`.toLowerCase().includes(search.value.toLowerCase())))
  return sortGenerations(filtered, sort.value)
})
onMounted(() => { void store.list().catch(() => undefined) })
function play(item: Generation) { const c=item.candidates[0]; if(!c)return; player.select({requestId:item.request_id,audioId:c.audio_id,title:c.title,subtitle:item.user_request,audioUrl:c.audio_url,coverUrl:c.cover_url,downloadUrl:c.download_url}) }
const when = (iso:string) => { const delta=Date.now()-new Date(iso).getTime(); return delta<300000?'刚刚':delta<86400000?new Date(iso).toLocaleTimeString('zh-CN',{hour:'2-digit',minute:'2-digit'}):new Date(iso).toLocaleDateString('zh-CN',{month:'numeric',day:'numeric'}) }
const statusOf = (item: Generation) => normalizeGenerationStatus(item.status)
</script>
<template><AppShell><section class="works-page"><header class="page-heading"><h1>我的作品</h1><p><SparklesIcon/>查看、试听和下载你的历史创作</p></header>
  <div class="work-filters"><label class="search"><MagnifyingGlassIcon/><input v-model="search" placeholder="搜索歌曲或创作描述"/></label><select v-model="status"><option value="">全部状态</option><option value="completed">已完成</option><option value="generating">生成中</option><option value="stopped">已停止等待</option><option value="failed">失败</option><option value="interrupted">服务中断</option></select><select v-model="sort"><option value="newest">最近生成</option><option value="oldest">最早生成</option></select><RouterLink class="button primary" to="/create"><SparklesIcon/>创作新歌曲</RouterLink></div>
  <p v-if="store.error" class="error-copy" role="alert">{{ store.error }}</p>
  <section class="works-table"><div class="table-head"><span>歌曲与创作描述</span><span>生成时间</span><span>状态</span><span>候选版本</span><span>操作</span></div>
    <div v-if="!rows.length" data-testid="works-empty" class="empty-state">还没有作品。描述一个想法，开始创作第一首歌曲吧。</div>
    <article v-for="item in rows" :key="item.request_id" class="work-row"><div class="work-song"><button v-if="statusOf(item)==='completed'" class="round small primary" @click="play(item)"><PlayIcon/></button><span v-else class="round small ghost"><MusicalNoteIcon/></span><img :src="item.candidates[0]?.cover_url || '/covers/night-study-a.png'" :alt="`${item.candidates[0]?.title || '歌曲'}封面`"/><div><strong>{{ item.candidates[0]?.title || '未命名歌曲' }}</strong><small>{{ item.user_request }}</small></div></div><span>{{ when(item.created_at) }}</span><div><span class="badge" :class="statusOf(item)">{{ generationStatusCopy(statusOf(item)) }}</span><small v-if="statusOf(item)==='generating'">{{ generationStatusCopy(item.stage) }} · {{ item.progress }}%</small><small v-if="statusOf(item)==='failed'">{{ item.error?.message || '生成失败' }}</small></div><span>{{ statusOf(item)==='completed' ? `${item.candidates.length} 个版本` : '—' }}</span><div class="row-actions"><template v-if="statusOf(item)==='completed'"><button class="round" @click="play(item)"><PlayIcon/></button><a :href="item.candidates[0]?.download_url"><ArrowDownTrayIcon/>下载</a></template><RouterLink v-else-if="statusOf(item)==='generating'" :to="`/generations/${item.request_id}`">查看进度</RouterLink><button v-else-if="statusOf(item)==='interrupted' || statusOf(item)==='stopped'" class="link" @click="store.resume(item.request_id)">继续查询</button><RouterLink v-else to="/create">重新创作</RouterLink><button class="icon-button"><EllipsisVerticalIcon/></button></div></article>
    <footer><span>已显示 {{ rows.length }} 个创作任务</span><div class="pagination"><button disabled>‹</button><button class="active">1</button><button disabled>›</button><select><option>10 条/页</option></select></div></footer>
  </section></section><GlobalPlayer/></AppShell></template>
