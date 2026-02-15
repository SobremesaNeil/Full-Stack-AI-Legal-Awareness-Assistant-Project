<template>
  <div class="chat-container">
    <!-- Decorative icons -->
    <div class="decorative-icons">
      <v-icon
        v-for="(icon, index) in decorativeIcons"
        :key="index"
        class="floating-icon"
        :icon="icon.name"
        :size="icon.size"
        color="primary"
        :style="icon.style"
      />
    </div>

    <div class="chat-header">
      <SessionSelector
        v-model="currentSessionId"
        :sessions="sessions"
        :loading="loading"
        @delete="deleteSessionById"
        @create="createNewSession"
        @update:modelValue="handleSessionChange"
      />
    </div>

    <div class="chat-messages" ref="messagesContainer">
      <div v-if="!messages.length" class="empty-state">
        <v-icon
          icon="mdi-chat-processing"
          size="64"
          color="primary"
          style="opacity: 0.2"
        />
        <p class="text-body-1 text-medium-emphasis">开始新的对话...</p>
      </div>
      <ChatMessageComponent
        v-else
        v-for="(message, index) in messages"
        :key="index"
        :message="message"
      />
    </div>

    <ChatInput
      :loading="loading"
      @send="sendMessage"
    />

    <!-- Snackbar for notifications -->
    <v-snackbar
      v-model="snackbar"
      :color="snackbarColor"
      :timeout="3000"
    >
      {{ snackbarText }}
      
      <template v-slot:actions>
        <v-btn
          variant="text"
          @click="snackbar = false"
        >
          关闭
        </v-btn>
      </template>
    </v-snackbar>

    <!-- Dialog for confirmations -->
    <ConfirmDialog
      v-model="dialog"
      :title="dialogTitle"
      :text="dialogText"
      confirm-text="确定"
      cancel-text="取消"
      :type="dialogType"
      @confirm="handleDialogConfirm"
      @cancel="handleDialogCancel"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, nextTick, onBeforeUnmount } from 'vue'
import { createSession, getSession, getWebSocketUrl, deleteSession } from '@/services/api'
import { saveSessionId, getSessionId, clearSessionId } from '@/utils/storage'
import type { Message, Session } from '@/types/chat' // 修正类型导入
import ChatMessageComponent from './ChatMessage.vue'
import SessionSelector from './SessionSelector.vue'
import ChatInput from './ChatInput.vue'
import ConfirmDialog from './ConfirmDialog.vue'

// State
const messages = ref<Message[]>([])
// const context = ref<Message[]>([]) // 暂时不需要 context 单独维护，messages 足够
const loading = ref(false)
const messagesContainer = ref<HTMLElement | null>(null)
const ws = ref<WebSocket | null>(null)
const sessionId = ref<string | null>(null)
const sessions = ref<Session[]>([]) // 修正类型
const currentSessionId = ref<string>('')

// UI State
const snackbar = ref(false)
const snackbarText = ref('')
const snackbarColor = ref<'success' | 'error' | 'warning'>('success')
const dialog = ref(false)
const dialogTitle = ref('')
const dialogText = ref('')
const dialogType = ref<'info' | 'warning' | 'error'>('info')
const dialogPromise = ref<{ resolve: (value: boolean) => void } | null>(null)

// Decorative icons configuration
const decorativeIcons = [
  { name: 'mdi-message-text-outline', size: '32', style: 'opacity: 0.1; position: absolute; top: 40px; right: 80px;' },
  { name: 'mdi-chat-processing-outline', size: '24', style: 'opacity: 0.1; position: absolute; top: 100px; right: 40px;' },
  { name: 'mdi-message-outline', size: '28', style: 'opacity: 0.1; position: absolute; top: 70px; right: 140px;' }
]

// WebSocket
const connectWebSocket = () => {
  if (!sessionId.value) return
  
  const wsUrl = getWebSocketUrl(sessionId.value)
  
  if (ws.value) {
    ws.value.close()
  }
  
  ws.value = new WebSocket(wsUrl)

  ws.value.onopen = () => {
    console.log('WebSocket connected')
    loading.value = false
  }

  ws.value.onmessage = (event) => {
    try {
      // 解析后端返回的消息
      const data = JSON.parse(event.data)
      
      // 构造符合前端类型的 Message 对象
      const aiMessage: Message = {
        role: 'assistant', // 后端返回的 role 
        content: data.content,
        type: data.type || 'text',
        mediaUrl: data.mediaUrl || data.media_url, // 兼容处理，防止后端没改
        created_at: new Date().toISOString()
      }

      messages.value.push(aiMessage)
      loading.value = false
      scrollToBottom()
    } catch (error) {
      console.error('Failed to parse message:', error)
      showMessage('接收消息时发生错误', 'error')
      loading.value = false
    }
  }

  ws.value.onclose = (event) => {
    console.log('WebSocket closed:', event.code, event.reason)
    // 只有非正常关闭才重连，且不是正在切换会话时
    if (!event.wasClean && sessionId.value) {
      // showMessage('连接已断开，正在尝试重连...', 'warning')
      setTimeout(connectWebSocket, 3000)
    }
  }

  ws.value.onerror = (event) => {
    console.error('WebSocket error:', event)
    loading.value = false
  }
}

// Session management
const loadSessions = async () => {
  try {
    const response = await fetch('http://localhost:8000/sessions/') // 确保 URL 完整，或者在 vite.config.ts 配置了 proxy
    if (!response.ok) throw new Error('Failed to load sessions')
    const data = await response.json()
    sessions.value = data
  } catch (error) {
    console.error('Failed to load sessions:', error)
    // showMessage('加载会话列表失败', 'error')
  }
}

const loadSession = async (selectedSessionId: string) => {
  try {
    const session = await getSession(selectedSessionId)
    sessionId.value = selectedSessionId
    // 确保后端返回的历史消息字段也被映射 (如果后端历史记录没存 camelCase)
    messages.value = session.messages.map((msg: any) => ({
        ...msg,
        mediaUrl: msg.media_url || msg.mediaUrl // 兼容历史数据
    }))
    saveSessionId(selectedSessionId)
    await connectWebSocket()
  } catch (error) {
    console.error('Failed to load session:', error)
    showMessage('加载会话失败', 'error')
  }
}

const createNewSession = async () => {
  try {
    if (ws.value) {
      ws.value.close()
    }

    const session = await createSession()
    sessionId.value = session.id // 注意：schemas.py 里 Session 定义的是 id，不是 session_id
    currentSessionId.value = session.id
    messages.value = []
    saveSessionId(session.id)
    await connectWebSocket()
    await loadSessions()
  } catch (error) {
    console.error('Failed to create new session:', error)
    showMessage('创建新会话失败', 'error')
  }
}

const deleteSessionById = async (sessionToDelete: string) => {
  try {
    const confirmed = await showConfirmDialog(
      '警告',
      '确定要删除此会话吗？此操作不可恢复。',
      'error'
    )

    if (!confirmed) return

    if (sessionToDelete === currentSessionId.value) {
      if (ws.value) {
        ws.value.close()
        ws.value = null
      }
      messages.value = []
      clearSessionId()
    }

    // 假设 api.ts 里有 deleteSession，如果没有需要补充
    // await deleteSession(sessionToDelete) 
    // 这里的 backend/main.py 并没有写 DELETE /sessions/{id} 的接口
    // 如果你没有实现删除接口，这里会报错。暂时先注释掉实际调用
    showMessage('后端暂未实现删除接口', 'warning')
    
    // await loadSessions()

    // if (sessionToDelete === currentSessionId.value) {
    //   currentSessionId.value = ''
    //   sessionId.value = null
    //   await createNewSession()
    // }

  } catch (error) {
    console.error('Failed to delete session:', error)
    showMessage('删除会话失败', 'error')
  }
}

// Message handling - 核心修复部分
const sendMessage = (text: string, type: 'text' | 'image' | 'audio' = 'text', url?: string, dialect?: string) => {
  // 检查 WebSocket 状态
  if (!ws.value || ws.value.readyState !== WebSocket.OPEN) {
    showMessage('连接已断开，正在重连...', 'warning')
    connectWebSocket()
    return
  }

  // 1. 构建前端临时显示的消息对象
  const userMessage: Message = {
    role: 'user',
    content: text || (type === 'image' ? '发送了一张图片' : '发送了一条语音'),
    type: type,
    mediaUrl: url,
    created_at: new Date().toISOString()
  }

  try {
    // 2. 乐观更新
    messages.value.push(userMessage)
    scrollToBottom()
    loading.value = true

    // 3. 发送给后端
    ws.value.send(JSON.stringify({
      content: text,
      type: type,
      url: url,
      dialect: dialect
    }))

  } catch (error) {
    console.error('Failed to send message:', error)
    showMessage('消息发送失败', 'error')
    loading.value = false
  }
}

// UI helpers
const scrollToBottom = async () => {
  await nextTick()
  if (messagesContainer.value) {
    messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight
  }
}

const showMessage = (text: string, color: 'success' | 'error' | 'warning' = 'success') => {
  snackbarText.value = text
  snackbarColor.value = color
  snackbar.value = true
}

const showConfirmDialog = (title: string, text: string, type: 'info' | 'warning' | 'error' = 'info'): Promise<boolean> => {
  return new Promise((resolve) => {
    dialogTitle.value = title
    dialogText.value = text
    dialogType.value = type
    dialog.value = true
    dialogPromise.value = { resolve }
  })
}

const handleDialogConfirm = () => {
  dialog.value = false
  dialogPromise.value?.resolve(true)
}

const handleDialogCancel = () => {
  dialog.value = false
  dialogPromise.value?.resolve(false)
}

const handleSessionChange = async (newSessionId: string) => {
  if (newSessionId && newSessionId !== sessionId.value) {
    await loadSession(newSessionId)
  }
}

// Lifecycle
onMounted(async () => {
  await loadSessions()
  
  let storedSessionId = getSessionId()
  
  if (storedSessionId) {
    try {
      // 尝试加载旧会话，如果失败（比如后端重启数据库清空），则创建新的
      await loadSession(storedSessionId)
    } catch {
      console.log('Session expired, creating new one')
      storedSessionId = null
    }
  }
  
  if (!storedSessionId) {
    await createNewSession()
  }
})

onBeforeUnmount(() => {
  if (ws.value) {
    ws.value.close()
  }
})
</script>

<style scoped>
.chat-container {
  display: flex;
  flex-direction: column;
  height: 100vh;
  width: 600px;
  margin: 0 auto;
  padding: 20px;
  background: rgb(var(--v-theme-surface));
  border-radius: 12px;
  box-shadow: 0 8px 30px rgba(0, 0, 0, 0.1);
  position: relative;
}

.decorative-icons {
  position: absolute;
  top: 0;
  right: 0;
  width: 100%;
  height: 100%;
  pointer-events: none;
  overflow: hidden;
}

.chat-header {
  width: 100%;
  margin-bottom: 20px;
  padding: 16px;
  background: rgb(var(--v-theme-surface));
  border-radius: 12px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
  z-index: 1;
}

.chat-messages {
  flex: 1;
  width: 100%;
  overflow-y: auto;
  padding: 16px;
  margin-bottom: 20px;
  background: rgb(var(--v-theme-surface));
  border-radius: 12px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
  min-height: 400px;
  z-index: 1;
}

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 400px;
  width: 100%;
  gap: 16px;
  color: rgba(var(--v-theme-on-surface), 0.6);
}

.floating-icon {
  animation: float 3s ease-in-out infinite;
  pointer-events: none;
  z-index: 0;
}

@keyframes float {
  0%, 100% {
    transform: translateY(0);
  }
  50% {
    transform: translateY(-10px);
  }
}

/* 添加媒体查询以支持小屏幕 */
@media (max-width: 840px) {
  .chat-container {
    width: 100%;
    max-width: 800px;
    margin: 0;
    border-radius: 0;
  }
}
</style> 