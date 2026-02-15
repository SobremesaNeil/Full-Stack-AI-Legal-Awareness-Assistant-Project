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
import { ref, onMounted, nextTick, onBeforeUnmount, computed } from 'vue'
import { createSession, getSession, getWebSocketUrl, deleteSession } from '@/services/api'
import { saveSessionId, getSessionId, clearSessionId } from '@/utils/storage'
import type { Message, ChatMessage, ChatSession } from '@/types/chat'
import ChatMessageComponent from './ChatMessage.vue'
import SessionSelector from './SessionSelector.vue'
import ChatInput from './ChatInput.vue'
import ConfirmDialog from './ConfirmDialog.vue'

// State
const messages = ref<Message[]>([])
const context = ref<ChatMessage[]>([])
const loading = ref(false)
const messagesContainer = ref<HTMLElement | null>(null)
const ws = ref<WebSocket | null>(null)
const sessionId = ref<string | null>(null)
const sessions = ref<ChatSession[]>([])
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
  {
    name: 'mdi-message-text-outline',
    size: '32',
    style: 'opacity: 0.1; position: absolute; top: 40px; right: 80px;'
  },
  {
    name: 'mdi-chat-processing-outline',
    size: '24',
    style: 'opacity: 0.1; position: absolute; top: 100px; right: 40px;'
  },
  {
    name: 'mdi-message-outline',
    size: '28',
    style: 'opacity: 0.1; position: absolute; top: 70px; right: 140px;'
  }
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
      const response = JSON.parse(event.data) as ChatMessage
      messages.value.push(response)
      context.value.push(response)
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
    if (!event.wasClean) {
      showMessage('WebSocket连接已断开，正在尝试重新连接...', 'warning')
      setTimeout(connectWebSocket, 3000)
    }
  }

  ws.value.onerror = (event) => {
    console.error('WebSocket error:', event)
    showMessage('WebSocket连接错误', 'error')
    loading.value = false
  }
}

// Session management
const loadSessions = async () => {
  try {
    const response = await fetch('/api/sessions/')
    if (!response.ok) throw new Error('Failed to load sessions')
    const data = await response.json()
    sessions.value = data
  } catch (error) {
    console.error('Failed to load sessions:', error)
    showMessage('加载会话列表失败', 'error')
  }
}

const loadSession = async (selectedSessionId: string) => {
  try {
    const session = await getSession(selectedSessionId)
    sessionId.value = selectedSessionId
    messages.value = session.messages
    context.value = session.context
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
    sessionId.value = session.session_id
    currentSessionId.value = session.session_id
    messages.value = []
    context.value = []
    saveSessionId(session.session_id)
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

    // 如果删除的是当前会话
    if (sessionToDelete === currentSessionId.value) {
      if (ws.value) {
        ws.value.close()
        ws.value = null
      }
      messages.value = []
      context.value = []
      clearSessionId()
    }

    await deleteSession(sessionToDelete)
    await loadSessions()

    // 如果删除的是当前会话，创建新会话
    if (sessionToDelete === currentSessionId.value) {
      currentSessionId.value = ''
      sessionId.value = null
      await createNewSession()
    }

    showMessage('会话已删除')
  } catch (error) {
    console.error('Failed to delete session:', error)
    showMessage('删除会话失败', 'error')
  }
}

// Message handling
const sendMessage = async (content: string) => {
  if (!ws.value || ws.value.readyState !== WebSocket.OPEN) {
    showMessage('WebSocket未连接', 'error')
    return
  }
  
 // 修改 sendMessage 函数以接收多模态参数
const sendMessage = (text: string, type: 'text' | 'image' | 'audio' = 'text', url?: string, dialect?: string) => {
  if (!websocket.value) {
    showMessage('连接已断开，请刷新页面', 'error')
    return
  }

  // 1. 构建符合后端标准的消息对象
  const userMessage: Message = {
    role: 'user',
    content: text || (type === 'image' ? '发送了一张图片' : '发送了一条语音'), // 如果没文字，给个默认提示
    type: type,          // 新增：告诉后端这是图片还是文字
    mediaUrl: url,       // 新增：文件的网络地址
    created_at: new Date().toISOString()
  }

  try {
    // 2. 乐观更新：先显示在界面上，不用等后端回传
    messages.value.push(userMessage)
    
    // 3. 滚动到底部
    scrollToBottom()

    // 4. 发送给后端 (JSON 格式)
    // 注意：这里发送的字段名要跟后端 main.py 里的 user_input.get(...) 对应
    websocket.value.send(JSON.stringify({
      content: text,
      type: type,
      url: url,
      dialect: dialect // 将用户选择的方言传给后端
    }))

  } catch (error) {
    console.error('Failed to send message:', error)
    showMessage('消息发送失败', 'error')
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

// 添加 handleSessionChange 函数
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
      const session = await getSession(storedSessionId)
      sessionId.value = storedSessionId
      currentSessionId.value = storedSessionId
      messages.value = session.messages
      context.value = session.context
    } catch {
      storedSessionId = null
    }
  }
  
  if (!storedSessionId) {
    const session = await createSession()
    sessionId.value = session.session_id
    currentSessionId.value = session.session_id
    saveSessionId(session.session_id)
    context.value = []
  }
  
  await connectWebSocket()
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