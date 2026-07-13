import { createRouter, createWebHistory } from 'vue-router'
import CreatePage from './pages/CreatePage.vue'
import GeneratingPage from './pages/GeneratingPage.vue'
import ResultPage from './pages/ResultPage.vue'
import WorksPage from './pages/WorksPage.vue'
import PreferencesPage from './pages/PreferencesPage.vue'

export const router = createRouter({ history: createWebHistory(), routes: [
  { path: '/', redirect: '/create' }, { path: '/create', component: CreatePage }, { path: '/generations/:id', component: GeneratingPage },
  { path: '/generations/:id/result', component: ResultPage }, { path: '/works', component: WorksPage }, { path: '/preferences', component: PreferencesPage },
] })
