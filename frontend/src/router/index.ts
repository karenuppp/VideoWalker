import { createRouter, createWebHistory, RouteRecordRaw } from 'vue-router'
import AdminDashboardView from '../views/AdminDashboardView.vue'
import UserAlertsView from '../views/UserAlertsView.vue'

const routes: Array<RouteRecordRaw> = [
  {
    path: '/',
    redirect: '/user/alerts'
  },
  {
    path: '/admin',
    redirect: '/admin/dashboard'
  },
  {
    path: '/admin/dashboard',
    name: 'admin-dashboard',
    component: AdminDashboardView
  },
  {
    path: '/user',
    redirect: '/user/alerts'
  },
  {
    path: '/user/alerts',
    name: 'user-alerts',
    component: UserAlertsView
  },
]

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes
})

export default router
