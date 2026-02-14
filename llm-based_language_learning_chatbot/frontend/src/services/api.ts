interface Message {
  role: 'user' | 'assistant'
  content: string
  created_at?: string
}

interface ChatMessage {
  role: 'user' | 'assistant'
  content: string
}

interface ChatSession {
  id: number
  session_id: string
  created_at: string
  updated_at: string
  context: ChatMessage[]
  messages: Message[]
}

// 使用相对路径，让Vite代理处理
const API_BASE_URL = '/api'
const WS_BASE_URL = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
const WS_HOST = window.location.host

export async function createSession(): Promise<ChatSession> {
  const response = await fetch(`${API_BASE_URL}/sessions/`, {
    method: 'POST'
  })
  if (!response.ok) {
    throw new Error('Failed to create session')
  }
  return response.json()
}

export async function getSession(sessionId: string): Promise<ChatSession> {
  const response = await fetch(`${API_BASE_URL}/sessions/${sessionId}`)
  if (!response.ok) {
    throw new Error('Failed to get session')
  }
  return response.json()
}

export function getWebSocketUrl(sessionId: string): string {
  // 去掉中间多余的斜杠
  return `${WS_BASE_URL}//${WS_HOST}/ws/${sessionId}`.replace('///', '//');
  // 或者更简单的：
  // return `${WS_BASE_URL}//${WS_HOST}/ws/${sessionId}`; 
}

export async function deleteSession(sessionId: string): Promise<void> {
  const response = await fetch(`${API_BASE_URL}/sessions/${sessionId}`, {
    method: 'DELETE'
  })
  if (!response.ok) {
    throw new Error('Failed to delete session')
  }
}

export type { Message, ChatMessage, ChatSession } 