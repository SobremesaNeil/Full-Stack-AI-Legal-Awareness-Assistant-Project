<template>
  <v-list lines="one" nav density="compact" class="bg-transparent">
    <v-list-subheader class="text-uppercase font-weight-bold text-caption mb-2">历史记录</v-list-subheader>
    
    <v-hover v-for="session in sortedSessions" :key="session.id" v-slot="{ isHovering, props }">
      <v-list-item
        v-bind="props"
        :value="session.id"
        :active="modelValue === session.id"
        color="primary"
        rounded="lg"
        class="mb-1 session-item"
        @click="$emit('update:modelValue', session.id)"
      >
        <template v-slot:prepend>
          <v-icon icon="mdi-message-text-outline" size="small" class="mr-2 text-medium-emphasis"></v-icon>
        </template>
        
        <v-list-item-title class="text-body-2">
          {{ formatSessionTitle(session) }}
        </v-list-item-title>

        <template v-slot:append>
          <v-btn
            v-if="isHovering || modelValue === session.id"
            icon="mdi-delete-outline"
            variant="text"
            size="x-small"
            color="error"
            @click.stop="$emit('delete', session.id)"
          ></v-btn>
        </template>
      </v-list-item>
    </v-hover>
  </v-list>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { Session } from '@/types/chat'

const props = defineProps<{
  modelValue: string
  sessions: Session[]
  loading: boolean
}>()

defineEmits(['update:modelValue', 'delete', 'create'])

const sortedSessions = computed(() => {
  // 按时间倒序
  return [...props.sessions].sort((a, b) => 
    new Date(b.created_at || 0).getTime() - new Date(a.created_at || 0).getTime()
  )
})

// 生成一个看起来像标题的文本（取第一条消息或默认文本）
const formatSessionTitle = (session: Session) => {
  const firstMsg = session.messages?.[0]
  if (firstMsg && firstMsg.content) {
    return firstMsg.content.length > 12 ? firstMsg.content.slice(0, 12) + '...' : firstMsg.content
  }
  return `新对话 ${session.id.slice(0, 4)}`
}
</script>

<style scoped>
.session-item {
  transition: all 0.2s;
}
</style>