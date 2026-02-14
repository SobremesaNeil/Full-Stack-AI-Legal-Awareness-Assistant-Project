<template>
  <div :class="['message', message.role]">
    <v-avatar :color="message.role === 'user' ? 'primary' : 'success'" size="40">
      <v-icon>{{ message.role === 'user' ? 'mdi-account' : 'mdi-robot' }}</v-icon>
    </v-avatar>
    <div class="message-content">
      <div class="markdown-body" v-html="renderedContent"></div>
      <span class="message-time">{{ formattedTime }}</span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { Message } from '@/types/chat'
import md from '@/utils/markdown'

const props = defineProps<{
  message: Message
}>()

const renderedContent = computed(() => {
  return md.render(props.message.content)
})

const formattedTime = computed(() => {
  if (!props.message.created_at) return ''
  return new Date(props.message.created_at).toLocaleString()
})
</script>

<style scoped>
.message {
  display: flex;
  gap: 12px;
  margin-bottom: 16px;
  padding: 12px;
  border-radius: 12px;
  background: rgba(var(--v-theme-surface-variant), 0.5);
  transition: transform 0.2s ease;
  width: 100%;
}

.message:hover {
  transform: translateY(-1px);
}

.message.user {
  background: rgba(var(--v-theme-primary), 0.1);
}

.message-content {
  flex: 1;
  position: relative;
  min-width: 0;
}

.message-content p {
  margin: 0;
  line-height: 1.5;
  white-space: pre-wrap;
  word-break: break-word;
}

.message-time {
  position: absolute;
  bottom: -15px;
  right: 0;
  font-size: 12px;
  color: rgba(var(--v-theme-on-surface), 0.6);
}

.markdown-body {
  margin: 0;
  line-height: 1.5;
  word-break: break-word;
}

.markdown-body :deep(p) {
  margin: 0.5em 0;
  white-space: normal;
}

.markdown-body :deep(pre) {
  background: rgba(var(--v-theme-surface), 0.8);
  padding: 1em;
  border-radius: 8px;
  overflow-x: auto;
  white-space: pre;
}

.markdown-body :deep(code) {
  background: rgba(var(--v-theme-surface), 0.8);
  padding: 0.2em 0.4em;
  border-radius: 4px;
  font-family: monospace;
  white-space: pre-wrap;
}

.markdown-body :deep(pre code) {
  padding: 0;
  background: none;
  white-space: pre;
}
</style> 