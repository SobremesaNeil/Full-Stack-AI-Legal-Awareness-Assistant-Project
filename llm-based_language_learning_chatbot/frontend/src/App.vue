<script setup lang="ts">
import { RouterView, useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const authStore = useAuthStore()
const router = useRouter()

// 退出登录处理
const handleLogout = () => {
  authStore.logout()
  router.push('/login')
}
</script>

<template>
  <v-app>
    <v-app-bar color="white" elevation="1" density="comfortable">
      <v-app-bar-title class="font-weight-bold text-primary d-flex align-center">
        <span class="mr-2">⚖️</span> AI 普法小助手
      </v-app-bar-title>

      <v-spacer></v-spacer>

      <v-btn to="/" variant="text" class="mr-1">首页</v-btn>
      <v-btn to="/about" variant="text" class="mr-1">关于</v-btn>

      <template v-if="authStore.isAuthenticated">
        <v-btn 
          v-if="authStore.isExpert" 
          to="/admin" 
          color="secondary" 
          variant="flat" 
          class="mr-3"
          prepend-icon="mdi-shield-account"
        >
          专家后台
        </v-btn>
        
        <div class="d-flex flex-column align-end mr-4 d-none d-sm-flex">
          <span class="text-caption text-grey">当前用户</span>
          <span class="text-body-2 font-weight-medium text-primary">{{ authStore.user }}</span>
        </div>

        <v-btn 
          @click="handleLogout" 
          color="error" 
          variant="outlined" 
          size="small" 
          prepend-icon="mdi-logout"
        >
          退出
        </v-btn>
      </template>

      <template v-else>
        <v-btn 
          to="/login" 
          color="primary" 
          variant="flat" 
          prepend-icon="mdi-login"
        >
          登录 / 注册
        </v-btn>
      </template>
    </v-app-bar>

    <v-main class="bg-grey-lighten-5">
      <router-view v-slot="{ Component }">
        <transition name="fade" mode="out-in">
          <component :is="Component" />
        </transition>
      </router-view>
    </v-main>
  </v-app>
</template>

<style>
/* 全局样式调整 */
html, body {
  margin: 0;
  padding: 0;
  height: 100%;
  overflow: hidden; /* 防止双重滚动条 */
}

/* 页面切换动画 */
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.2s ease;
}
.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>