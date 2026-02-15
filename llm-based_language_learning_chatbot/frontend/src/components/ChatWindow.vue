<template>
  <v-layout class="fill-height rounded-0 overflow-hidden bg-grey-lighten-4">
    <v-navigation-drawer
      v-model="drawer"
      :permanent="mdAndUp"
      width="280"
      color="grey-lighten-5"
      class="border-e"
      elevation="0"
    >
      <div class="d-flex flex-column fill-height">
        <div class="pa-4">
          <v-btn
            block
            color="primary"
            variant="flat"
            size="large"
            prepend-icon="mdi-plus"
            class="text-capitalize rounded-lg font-weight-bold elevation-2"
            @click="createNewSession"
            :loading="loading"
          >
            开启新对话
          </v-btn>
        </div>

        <v-divider class="mx-4"></v-divider>

        <div class="flex-grow-1 overflow-y-auto pa-2 custom-scrollbar">
          <SessionSelector
            v-model="currentSessionId"
            :sessions="sessions"
            :loading="loading"
            @delete="deleteSessionById"
            @update:modelValue="handleSessionChange"
          />
        </div>
        
        <div class="pa-4 text-center">
          <div class="text-caption text-medium-emphasis">AI 普法小助手 v1.0</div>
          <div class="text-caption text-disabled mt-1">为您提供专业法律咨询</div>
        </div>
      </div>
    </v-navigation-drawer>

    <v-main class="d-flex flex-column position-relative h-screen bg-white">
      <v-app-bar v-if="!mdAndUp" density="compact" flat class="border-b">
        <v-app-bar-nav-icon @click="drawer = !drawer"></v-app-bar-nav-icon>
        <v-app-bar-title class="text-subtitle-1 font-weight-bold">普法助手</v-app-bar-title>
      </v-app-bar>

      <div 
        class="flex-grow-1 overflow-y-auto px-4 py-6" 
        ref="messagesContainer" 
        style="scroll-behavior: smooth;"
      >
        <v-container max-width="900" class="pa-0 h-100">
          
          <div v-if="!messages.length" class="d-flex flex-column align-center justify-center h-100" style="min-height: 60vh; opacity: 0.9">
            <v-avatar color="primary" variant="tonal" size="80" class="mb-6 elevation-1">
              <v-icon icon="mdi-scale-balance" size="40"></v-icon>
            </v-avatar>
            <h2 class="text-h5 font-weight-bold text-grey-darken-3 mb-2">有什么法律问题我可以帮您？</h2>
            <p class="text-body-1 text-grey-darken-1 text-center mb-8" style="max-width: 460px; line-height: 1.6;">
              我是您的 AI 法律顾问。我可以为您解答民法典、刑法相关疑问，分析合同风险，甚至为您生成案情思维导图。
            </p>
            
            <div class="d-flex gap-3 flex-wrap justify-center" style="max-width: 600px">
              <v-chip 
                v-for="qa in suggestedQuestions" 
                :key="qa"
                color="primary" 
                variant="outlined" 
                link 
                class="px-4 py-2"
                style="height: auto"
                @click="sendMessage(qa)"
              >
                {{ qa }}
              </v-chip>
            </div>
          </div>

          <template v-else>
            <div v-for="(message, index) in messages" :key="index" class="mb-6">
              <ChatMessageComponent :message="message" />
            </div>
          </template>

          <div style="height: 20px;"></div>
        </v-container>
      </div>

      <div class="py-4 px-4 bg-white w-100 border-t">
        <v-container max-width="900" class="pa-0">
          <ChatInput :loading="loading" @send="sendMessage" />
          <div class="text-center text-caption text-grey-lighten-1 mt-2">
            AI 生成内容仅供参考，不构成正式法律意见。
          </div>
        </v-container>
      </div>
    </v-main>

    <v-snackbar
      v-model="snackbar"
      :color="snackbarColor"
      location="top"
      variant="flat"
      elevation="4"
      class="mt-4"
    >
      {{ snackbarText }}
      <template v-slot:actions>
        <v-btn variant="text" icon="mdi-close" @click="snackbar = false"></v-btn>
      </template>
    </v-snackbar>

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
  </v-layout>
</template>

<script setup lang="ts">
import { ref, onMounted, nextTick, onBeforeUnmount } from 'vue'
import { useDisplay } from 'vuetify' // 引入 Vuetify 的响应式工具
import { createSession, getSession, getWebSocketUrl } from '@/services/api'
import { saveSessionId, getSessionId, clearSessionId } from '@/utils/storage'
import type { Message, Session } from '@/types/chat'
import ChatMessageComponent from './ChatMessage.vue'
import SessionSelector from './SessionSelector.vue'
import ChatInput from './ChatInput.vue'
import ConfirmDialog from './ConfirmDialog.vue'

// --- 响应式布局状态 ---
const { mdAndUp } = useDisplay()
const drawer = ref(true) // 侧边栏开关

// --- 快捷建议 ---
const suggestedQuestions = [
  '朋友借钱不还怎么办？',
  '租房合同有哪些常见陷阱？',
  '离婚时财产如何分割？',
  '公司无故辞退我合法吗？'
]

// --- State (保留您原有的状态变量) ---
const messages = ref<Message[]>([])
const loading = ref(false)
const messagesContainer = ref<HTMLElement | null>(null)
const ws = ref<WebSocket | null>(null)
const sessionId = ref<string | null>(null)
const sessions = ref<Session[]>([])
const currentSessionId = ref<string>('')

// --- UI State ---
const snackbar = ref(false)
const snackbarText = ref('')
const snackbarColor = ref<'success' | 'error' | 'warning'>('success')
const dialog = ref(false)
const dialogTitle = ref('')
const dialogText = ref('')
const dialogType = ref<'info' | 'warning' | 'error'>('info')
const dialogPromise = ref<{ resolve: (value: boolean) => void } | null>(null)

// --- WebSocket Logic (保留原逻辑) ---
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
      const data = JSON.parse(event.data)
      // 构造符合前端类型的 Message 对象
      const aiMessage: Message = {
        role: 'assistant',
        content: data.content,
        type: data.type || 'text',
        mediaUrl: data.mediaUrl || data.media_url, 
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
    if (!event.wasClean && sessionId.value) {
      setTimeout(connectWebSocket, 3000)
    }
  }

  ws.value.onerror = (event) => {
    console.error('WebSocket error:', event)
    loading.value = false
  }
}

// --- Session Management (保留原逻辑) ---
const loadSessions = async () => {
  try {
    const response = await fetch('http://localhost:8000/sessions/')
    if (!response.ok) throw new Error('Failed to load sessions')
    const data = await response.json()
    sessions.value = data
  } catch (error) {
    console.error('Failed to load sessions:', error)
  }
}

const loadSession = async (selectedSessionId: string) => {
  try {
    const session = await getSession(selectedSessionId)
    sessionId.value = selectedSessionId
    messages.value = session.messages.map((msg: any) => ({
        ...msg,
        mediaUrl: msg.media_url || msg.mediaUrl 
    }))
    saveSessionId(selectedSessionId)
    await connectWebSocket()
    // 切换会话后，如果是移动端，自动收起侧边栏
    if (!mdAndUp.value) drawer.value = false
    setTimeout(scrollToBottom, 100)
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
    sessionId.value = session.id
    currentSessionId.value = session.id
    messages.value = []
    saveSessionId(session.id)
    await connectWebSocket()
    await loadSessions()
    // 移动端自动收起侧边栏
    if (!mdAndUp.value) drawer.value = false
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

    // 后端暂时未实现删除接口的提示
    showMessage('后端暂未实现删除接口，仅演示前端交互', 'warning')
    
    // 待后端实现后解开：
    // await deleteSession(sessionToDelete) 
    // await loadSessions()
  } catch (error) {
    console.error('Failed to delete session:', error)
    showMessage('删除会话失败', 'error')
  }
}

const handleSessionChange = async (newSessionId: string) => {
  if (newSessionId && newSessionId !== sessionId.value) {
    await loadSession(newSessionId)
  }
}

// --- Message Sending (保留原逻辑) ---
const sendMessage = (text: string, type: 'text' | 'image' | 'audio' = 'text', url?: string, dialect?: string) => {
  if (!ws.value || ws.value.readyState !== WebSocket.OPEN) {
    showMessage('连接已断开，正在重连...', 'warning')
    connectWebSocket()
    return
  }

  const userMessage: Message = {
    role: 'user',
    content: text || (type === 'image' ? '发送了一张图片' : '发送了一条语音'),
    type: type,
    mediaUrl: url,
    created_at: new Date().toISOString()
  }

  try {
    messages.value.push(userMessage)
    scrollToBottom()
    loading.value = true

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

// --- Helpers ---
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

// --- Lifecycle ---
onMounted(async () => {
  await loadSessions()
  
  let storedSessionId = getSessionId()
  
  if (storedSessionId) {
    try {
      await loadSession(storedSessionId)
      currentSessionId.value = storedSessionId
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
/* 自定义滚动条样式 */
.custom-scrollbar::-webkit-scrollbar {
  width: 5px;
}
.custom-scrollbar::-webkit-scrollbar-track {
  background: transparent;
}
.custom-scrollbar::-webkit-scrollbar-thumb {
  background: #e0e0e0;
  border-radius: 4px;
}
.custom-scrollbar::-webkit-scrollbar-thumb:hover {
  background: #bdbdbd;
}

/* 覆盖 Vuetify 默认背景 */
.v-main {
  background-color: #ffffff;
}
</style>