<template>
  <div class="login-container">
    <div class="card">
      <h2>{{ isRegister ? '注册账号' : '登录系统' }}</h2>
      <form @submit.prevent="handleSubmit">
        <div class="form-group">
          <label>用户名</label>
          <input v-model="form.username" type="text" required />
        </div>
        <div class="form-group">
          <label>密码</label>
          <input v-model="form.password" type="password" required />
        </div>
        <button type="submit" :disabled="loading">
          {{ loading ? '处理中...' : (isRegister ? '注册' : '登录') }}
        </button>
      </form>
      <p class="switch-mode">
        {{ isRegister ? '已有账号？' : '还没有账号？' }}
        <a href="#" @click.prevent="isRegister = !isRegister">
          {{ isRegister ? '去登录' : '去注册' }}
        </a>
      </p>
      <p v-if="error" class="error">{{ error }}</p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { loginUser, registerUser } from '@/services/api'
import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const authStore = useAuthStore()

const isRegister = ref(false)
const loading = ref(false)
const error = ref('')
const form = ref({ username: '', password: '' })

async function handleSubmit() {
  loading.value = true
  error.value = ''
  try {
    if (isRegister.value) {
      await registerUser(form.value)
      // 注册成功后直接登录
      const res = await loginUser(form.value.username, form.value.password)
      authStore.login(res.access_token, form.value.username)
    } else {
      const res = await loginUser(form.value.username, form.value.password)
      authStore.login(res.access_token, form.value.username)
    }
    router.push('/')
  } catch (e: any) {
    error.value = e.message
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.login-container { display: flex; justify-content: center; align-items: center; height: 80vh; }
.card { background: white; padding: 2rem; border-radius: 12px; box-shadow: 0 4px 12px rgba(0,0,0,0.1); width: 100%; max-width: 400px; }
.form-group { margin-bottom: 1rem; }
input { width: 100%; padding: 0.5rem; margin-top: 0.5rem; border: 1px solid #ddd; border-radius: 4px; }
button { width: 100%; padding: 0.75rem; background: #2c3e50; color: white; border: none; border-radius: 4px; cursor: pointer; }
.switch-mode { text-align: center; margin-top: 1rem; font-size: 0.9rem; }
.error { color: red; text-align: center; margin-top: 1rem; }
</style>