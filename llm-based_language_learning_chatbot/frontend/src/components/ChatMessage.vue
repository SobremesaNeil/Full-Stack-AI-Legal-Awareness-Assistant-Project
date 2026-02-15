<template>
  <div :class="['d-flex', isUser ? 'justify-end' : 'justify-start', 'message-row']">
    
    <v-avatar v-if="!isUser" color="primary" variant="tonal" size="36" class="mr-3 align-self-start mt-1">
      <v-icon icon="mdi-scale-balance" size="20"></v-icon>
    </v-avatar>

    <div style="max-width: 85%;">
      <div v-if="!isUser" class="text-caption text-grey ml-1 mb-1">普法小助手</div>

      <v-sheet
        :color="isUser ? 'primary' : 'white'"
        :class="[
          'px-4 py-3',
          'elevation-1',
          isUser ? 'rounded-be-0' : 'rounded-bs-0', 
          'rounded-xl'
        ]"
        class="message-bubble position-relative"
      >
        <v-img
          v-if="message.mediaUrl && (message.type === 'image' || message.type === 'mindmap')"
          :src="message.mediaUrl"
          max-width="100%"
          max-height="400"
          class="rounded-lg bg-grey-lighten-4 mb-2"
          cover
        ></v-img>

        <div v-if="message.mediaUrl && message.type === 'audio'" class="d-flex align-center gap-2">
           <v-btn icon="mdi-play" variant="text" :color="isUser?'white':'primary'" size="small"></v-btn>
           <audio controls :src="message.mediaUrl" class="w-100" style="height: 32px;"></audio>
        </div>

        <div 
          v-if="message.content"
          class="markdown-body"
          :class="{ 'text-white': isUser }"
          v-html="renderedContent"
        ></div>
      </v-sheet>
      
      <div :class="['text-caption text-grey mt-1', isUser ? 'text-right mr-1' : 'ml-1']">
        {{ formatTime(message.created_at) }}
      </div>
    </div>

    <v-avatar v-if="isUser" color="grey-lighten-3" size="36" class="ml-3 align-self-start mt-1">
      <v-img src="https://api.dicebear.com/7.x/avataaars/svg?seed=Felix" alt="User"></v-img>
    </v-avatar>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { marked } from 'marked'
import type { Message } from '@/types/chat'

const props = defineProps<{
  message: Message
}>()

const isUser = computed(() => props.message.role === 'user')

const renderedContent = computed(() => {
  if (!props.message.content) return ''
  // 简单配置 marked
  return marked(props.message.content, { async: false })
})

const formatTime = (isoString?: string) => {
  if (!isoString) return ''
  const date = new Date(isoString)
  return date.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
}
</script>

<style scoped>
/* 针对用户气泡内的 markdown 进行特殊颜色覆盖 */
.markdown-body.text-white :deep(p),
.markdown-body.text-white :deep(h1),
.markdown-body.text-white :deep(h2),
.markdown-body.text-white :deep(li),
.markdown-body.text-white :deep(strong) {
  color: white !important;
}

.message-row {
  /* 简单的入场动画 */
  animation: slideIn 0.3s ease-out;
}

@keyframes slideIn {
  from { opacity: 0; transform: translateY(10px); }
  to { opacity: 1; transform: translateY(0); }
}
</style>