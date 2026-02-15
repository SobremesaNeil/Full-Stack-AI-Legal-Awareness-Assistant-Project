import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { jwtDecode } from 'jwt-decode'

interface UserPayload {
  sub: string // username
  exp: number
}

export const useAuthStore = defineStore('auth', () => {
  const token = ref<string | null>(localStorage.getItem('access_token'))
  const user = ref<string | null>(localStorage.getItem('username'))
  const role = ref<string>('user') // 简单处理，实际应从后端获取或解析Token

  const isAuthenticated = computed(() => !!token.value)
  const isExpert = computed(() => role.value === 'admin')

  function login(accessToken: string, username: string) {
    token.value = accessToken
    user.value = username
    
    // 简单判断：如果是 admin 账号，赋予管理员权限（演示用）
    if (username === 'admin') {
      role.value = 'admin'
    } else {
      role.value = 'user'
    }

    localStorage.setItem('access_token', accessToken)
    localStorage.setItem('username', username)
  }

  function logout() {
    token.value = null
    user.value = null
    role.value = 'user'
    localStorage.removeItem('access_token')
    localStorage.removeItem('username')
  }

  return { token, user, role, isAuthenticated, isExpert, login, logout }
})