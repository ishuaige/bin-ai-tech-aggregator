import { createRouter, createWebHistory } from 'vue-router'
import DashboardView from '../views/DashboardView.vue'
import SettingsView from '../views/SettingsView.vue'
import HistoryView from '../views/HistoryView.vue'
import ContentsView from '../views/ContentsView.vue'

const routes = [
  { path: '/', redirect: '/dashboard' },
  { path: '/dashboard', name: 'dashboard', component: DashboardView },
  { path: '/contents', name: 'contents', component: ContentsView },
  { path: '/settings', name: 'settings', component: SettingsView },
  { path: '/history', name: 'history', component: HistoryView },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

export default router
