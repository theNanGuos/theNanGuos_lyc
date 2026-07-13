import type { Generation } from '../api/client'

const now = Date.now()
const demoItems: Generation[] = [
  {
    request_id: 'demo-a', user_request: '中文 lo-fi pop · 温暖克制 · 女声', status: 'completed', stage: 'SUCCESS', progress: 100,
    task_id: 'task_9f3c7b2a45671d8e', created_at: new Date(now).toISOString(), updated_at: new Date(now).toISOString(),
    candidates: [
      { audio_id: 'a', title: '深夜微光 A', duration: 92, audio_url: '/demo-a/a.mp3', download_url: '#', cover_url: '/covers/night-study-a.png' },
      { audio_id: 'b', title: '深夜微光 B', duration: 88, audio_url: '/demo-a/b.mp3', download_url: '#', cover_url: '/covers/night-study-b.png' },
    ],
  },
  {
    request_id: 'demo-b', user_request: 'city pop · 轻快 · 男声', status: 'completed', stage: 'SUCCESS', progress: 100,
    created_at: new Date(now - 3_600_000).toISOString(), updated_at: new Date(now - 3_600_000).toISOString(),
    candidates: [{ audio_id: 'rain', title: '雨后的城市', duration: 88, audio_url: '', download_url: '#', cover_url: '/covers/rainy-city.png' }],
  },
  {
    request_id: 'demo-c', user_request: 'ambient · 纯音乐 · 空灵', status: 'generating', stage: 'FIRST_SUCCESS', progress: 80,
    task_id: 'task_demo_c', created_at: new Date(now - 86_400_000).toISOString(), updated_at: new Date(now - 60_000).toISOString(),
    candidates: [{ audio_id: 'galaxy', title: '无声星河', audio_url: '', download_url: '#', cover_url: '/covers/silent-galaxy.png' }],
  },
  {
    request_id: 'demo-d', user_request: 'indie pop · 明亮 · 女声', status: 'failed', stage: 'failed', progress: 100,
    error: { code: 'SENSITIVE_WORD_ERROR', message: '内容包含禁用词' }, created_at: new Date(now - 172_800_000).toISOString(), updated_at: new Date(now - 172_800_000).toISOString(),
    candidates: [{ audio_id: 'road', title: '夏日公路', audio_url: '', download_url: '#', cover_url: '/covers/summer-road.png' }],
  },
]

export const demoGenerations = () => demoItems.map(item => ({ ...item, candidates: item.candidates.map(candidate => ({ ...candidate })) }))
export const demoGeneration = (id: string) => demoGenerations().find(item => item.request_id === id)
export const isDemoId = (id: string) => /^demo-[a-z0-9-]+$/.test(id)
export const sortGenerations = (items: Generation[], order: 'newest' | 'oldest') => [...items].sort((a, b) => {
  const difference = new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
  return order === 'newest' ? difference : -difference
})
