<template>
  <div class="session-selector">
    <v-select
      v-model="currentSession"
      :items="sessions || []"
      placeholder="选择会话"
      persistent-placeholder
      hide-details
      class="session-select"
      return-object
      item-title="session_id"
      item-value="session_id"
    >
      <template v-slot:prepend>
        <v-icon>mdi-chat</v-icon>
      </template>
      <template v-slot:item="{ item, props }">
        <v-list-item v-bind="props">
          <template v-slot:prepend>
            <v-icon>mdi-chat-outline</v-icon>
          </template>
          <v-list-item-title>{{ formatSessionLabel(item.raw) }}</v-list-item-title>
          <template v-slot:append>
            <v-btn
              color="error"
              variant="text"
              density="compact"
              size="24"
              :disabled="loading"
              @click.stop="$emit('delete', item.raw.session_id)"
              class="delete-btn"
            >
              <v-icon size="16" color="error">mdi-close</v-icon>
            </v-btn>
          </template>
        </v-list-item>
      </template>
      <template v-slot:selection="{ item }">
        <div class="d-flex align-center">
          <v-icon size="small" class="mr-2">mdi-chat</v-icon>
          {{ formatSessionLabel(item.raw) }}
        </div>
      </template>
    </v-select>
    <v-btn
      color="primary"
      prepend-icon="mdi-plus"
      :disabled="loading"
      @click="$emit('create')"
      class="new-session-btn"
    >
      <span>新建会话</span>
    </v-btn>
  </div>
</template>

<script setup lang="ts">
import type { ChatSession } from '@/types/chat'
import { computed } from 'vue'

const props = defineProps<{
  modelValue: string | null
  sessions: ChatSession[]
  loading: boolean
}>()

const emit = defineEmits<{
  (e: 'update:modelValue', value: string): void
  (e: 'delete', sessionId: string): void
  (e: 'create'): void
}>()

const currentSession = computed({
  get: () => props.sessions.find(s => s.session_id === props.modelValue),
  set: (session: ChatSession | null) => {
    if (session) {
      emit('update:modelValue', session.session_id)
    }
  }
})

const formatSessionLabel = (session: ChatSession) => {
  if (!session) return '未知会话'

  let timeStr = '未知时间'
  try {
    const timestamp = session.created_at
    // 检查是否是ISO格式的字符串
    if (typeof timestamp === 'string' && timestamp.includes('T')) {
      const date = new Date(timestamp)
      if (!isNaN(date.getTime())) {
        const now = new Date()
        const isToday = date.toLocaleDateString() === now.toLocaleDateString()

        if (isToday) {
          timeStr = date.toLocaleTimeString('zh-CN', {
            hour: '2-digit',
            minute: '2-digit'
          })
          timeStr = `今天 ${timeStr}`
        } else {
          timeStr = date.toLocaleString('zh-CN', {
            month: '2-digit',
            day: '2-digit',
            hour: '2-digit',
            minute: '2-digit'
          })
        }
      }
    }
  } catch (error) {
    console.error('Error formatting date:', error)
  }

  const firstMessage = session.messages?.[0]?.content || '空会话'
  const preview = firstMessage.length > 20 ? firstMessage.slice(0, 20) + '...' : firstMessage

  return `${timeStr} - ${preview}`
}

</script>

<style scoped>
.session-selector {
  display: flex;
  gap: 16px;
  width: 100%;
}

.session-select {
  flex: 1;
}

:deep(.v-btn) {
  text-transform: none;
}

:deep(.v-btn__content) {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
}

:deep(.delete-btn) {
  opacity: 0.85;
  transition: all 0.2s ease;
  min-width: 24px;
  width: 24px;
  height: 24px;
  padding: 0;
  margin: 0 4px;
  border-radius: 4px;
}

:deep(.delete-btn:hover) {
  opacity: 1;
  transform: scale(1.15);
  background-color: rgba(var(--v-theme-error), 0.12);
}

:deep(.delete-btn:active) {
  transform: scale(0.9);
}

:deep(.delete-btn.v-btn--disabled) {
  opacity: 0.5;
}

:deep(.delete-btn .v-icon) {
  font-size: 16px;
  width: 16px;
  height: 16px;
}

.new-session-btn {
  min-width: 100px;
}

:deep(.v-select .v-field__input) {
  min-height: 44px;
  padding-top: 0;
  padding-bottom: 0;
}

:deep(.v-list-item-title) {
  font-size: 14px;
  line-height: 1.4;
}
</style> 