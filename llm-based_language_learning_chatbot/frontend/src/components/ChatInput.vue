<template>
  <div class="chat-input">
    <v-textarea
      v-model="inputValue"
      rows="3"
      placeholder="输入消息..."
      hide-details
      @keydown.ctrl.enter="handleSend"
      class="chat-textarea"
    ></v-textarea>
    <v-btn
      color="primary"
      :loading="loading"
      @click="handleSend"
      class="send-button"
    >
      <v-icon start>mdi-send</v-icon>
      <span>发送</span>
    </v-btn>
  </div>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'

const props = defineProps<{
  loading: boolean
}>()

const emit = defineEmits<{
  (e: 'send', message: string): void
}>()

const inputValue = ref('')

const handleSend = () => {
  const message = inputValue.value.trim()
  if (!message || props.loading) return
  
  emit('send', message)
  inputValue.value = ''
}
</script>

<style scoped>
.chat-input {
  display: flex;
  gap: 16px;
  padding: 16px;
  background: rgb(var(--v-theme-surface));
  border-radius: 12px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
}

.chat-textarea {
  flex: 1;
}

:deep(.v-btn) {
  text-transform: none;
  align-self: flex-end;
  margin-bottom: 4px;
}

:deep(.v-btn__content) {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
}

:deep(.v-textarea textarea) {
  min-height: 80px !important;
}
</style> 