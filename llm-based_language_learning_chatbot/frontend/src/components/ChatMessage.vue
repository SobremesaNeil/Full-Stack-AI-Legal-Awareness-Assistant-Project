<template>
  <div :class="['message', message.role]">
    <div class="avatar">
      {{ message.role === 'user' ? '👤' : '⚖️' }}
    </div>
    <div class="content-wrapper">
      <div class="bubble" v-html="parsedContent"></div>
      
      <img v-if="message.media_url" :src="message.media_url" class="media-img" />

      <div v-if="message.citations" class="citations">
        <h4>📚 法律依据:</h4>
        <div class="citation-text">{{ message.citations }}</div>
      </div>

      <div v-if="message.role === 'assistant'" class="feedback-actions">
        <button 
          @click="sendFeedback(1)" 
          :class="{ active: feedbackStatus === 1 }"
          title="回答准确"
        >👍</button>
        <button 
          @click="sendFeedback(-1)" 
          :class="{ active: feedbackStatus === -1 }"
          title="回答有误"
        >👎</button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { marked } from 'marked'
import { submitFeedback } from '@/services/api'
import type { Message } from '@/types/chat'

const props = defineProps<{ message: Message }>()
const feedbackStatus = ref(0) // 0=none, 1=like, -1=dislike

const parsedContent = computed(() => {
  return marked(props.message.content || '')
})

async function sendFeedback(score: number) {
  if (feedbackStatus.value === score) return // Prevent double click
  try {
    // 假设 message 对象里有 id (后端已返回)
    if (props.message.messageId) {
       await submitFeedback(props.message.messageId, score)
       feedbackStatus.value = score
       alert(score === 1 ? '感谢您的好评！' : '感谢反馈，专家稍后会进行纠偏。')
    }
  } catch (e) {
    console.error(e)
  }
}
</script>

<style scoped>
.message { display: flex; margin-bottom: 1.5rem; gap: 10px; }
.message.user { flex-direction: row-reverse; }
.avatar { font-size: 1.5rem; width: 40px; height: 40px; background: #eee; border-radius: 50%; display: flex; align-items: center; justify-content: center; }
.content-wrapper { max-width: 70%; display: flex; flex-direction: column; gap: 5px; }
.bubble { padding: 12px 16px; border-radius: 12px; line-height: 1.5; }
.user .bubble { background: #007bff; color: white; border-bottom-right-radius: 2px; }
.assistant .bubble { background: #f1f1f1; color: #333; border-bottom-left-radius: 2px; }
.media-img { max-width: 200px; border-radius: 8px; margin-top: 5px; }

/* 引用样式 */
.citations { font-size: 0.85rem; background: #fffbe6; border: 1px solid #ffe58f; padding: 8px; border-radius: 4px; color: #555; }
.citations h4 { margin: 0 0 4px 0; color: #d48806; font-size: 0.85rem; }
.citation-text { white-space: pre-wrap; }

/* 反馈按钮 */
.feedback-actions { display: flex; gap: 8px; margin-top: 4px; }
.feedback-actions button { background: none; border: none; cursor: pointer; opacity: 0.5; transition: opacity 0.2s; font-size: 1.1rem; }
.feedback-actions button:hover { opacity: 1; }
.feedback-actions button.active { opacity: 1; transform: scale(1.2); }
</style>