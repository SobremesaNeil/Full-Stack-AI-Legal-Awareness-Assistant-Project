import { createRouter, createWebHistory } from 'vue-router'
import HomeView from '../views/HomeView.vue'
import LoginView from '../views/LoginView.vue'
import AdminDashboard from '../views/AdminDashboard.vue'
import { useAuthStore } from '@/stores/auth'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    { path: '/', name: 'home', component: HomeView },
    { path: '/login', name: 'login', component: LoginView },
    { 
      path: '/admin', 
      name: 'admin', 
      component: AdminDashboard,
      meta: { requiresAuth: true, requiresExpert: true }
    },
    { path: '/about', name: 'about', component: () => import('../views/AboutView.vue') }
  ]
})

// 路由守卫
router.beforeEach((to, from, next) => {
  const authStore = useAuthStore()
  
  if (to.meta.requiresAuth && !authStore.isAuthenticated) {
    next('/login')
  } else if (to.meta.requiresExpert && !authStore.isExpert) {
    alert('无权访问专家后台')
    next('/')
  } else {
    next()
  }
})

export default router
