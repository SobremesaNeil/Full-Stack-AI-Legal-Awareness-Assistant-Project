<template>
  <div class="admin-dashboard">
    <h1>👨‍⚖️ 专家工作台</h1>
    <div v-if="loading">加载中...</div>
    <div v-else class="ticket-list">
      <div v-for="ticket in tickets" :key="ticket.id" class="ticket-card">
        <div class="ticket-header">
          <h3>{{ ticket.title }}</h3>
          <span :class="['status', ticket.status]">{{ ticket.status }}</span>
        </div>
        <p class="desc">{{ ticket.description }}</p>
        <div class="meta">用户ID: {{ ticket.id }} | 时间: {{ new Date(ticket.created_at).toLocaleString() }}</div>
        
        <div v-if="ticket.expert_reply" class="reply-box">
          <strong>专家回复：</strong> {{ ticket.expert_reply }}
        </div>
        
        <div v-else class="action-box">
          <textarea v-model="replyText[ticket.id]" placeholder="输入法律意见..."></textarea>
          <button @click="handleReply(ticket.id)">提交回复</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { getAdminTickets, replyTicket } from '@/services/api'

const tickets = ref<any[]>([])
const loading = ref(true)
const replyText = ref<Record<number, string>>({})

async function loadTickets() {
  loading.value = true
  try {
    tickets.value = await getAdminTickets()
  } catch (e) {
    alert('无法加载工单，请确认您是管理员')
  } finally {
    loading.value = false
  }
}

async function handleReply(id: number) {
  const text = replyText.value[id]
  if (!text) return
  await replyTicket(id, text)
  await loadTickets() // 刷新列表
  replyText.value[id] = ''
}

onMounted(loadTickets)
</script>

<style scoped>
.admin-dashboard { padding: 2rem; max-width: 800px; margin: 0 auto; }
.ticket-card { background: white; border: 1px solid #eee; padding: 1.5rem; margin-bottom: 1rem; border-radius: 8px; }
.ticket-header { display: flex; justify-content: space-between; align-items: center; }
.status { padding: 2px 8px; border-radius: 4px; font-size: 0.8rem; }
.status.pending { background: #fff3cd; color: #856404; }
.status.answered { background: #d4edda; color: #155724; }
.desc { color: #555; margin: 10px 0; }
.meta { font-size: 0.8rem; color: #999; }
.action-box textarea { width: 100%; height: 80px; margin: 10px 0; padding: 8px; }
.action-box button { background: #007bff; color: white; border: none; padding: 8px 16px; border-radius: 4px; cursor: pointer; }
.reply-box { background: #f8f9fa; padding: 10px; margin-top: 10px; border-left: 3px solid #007bff; }
</style>