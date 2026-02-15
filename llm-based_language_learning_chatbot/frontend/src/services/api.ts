import type { Message, Session } from '@/types/chat'

// 优化：优先使用环境变量，如果没有则回退到 localhost
// 请在前端根目录新建 .env 文件，写入 VITE_API_BASE_URL=http://your-server-ip:8000
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

// 自动根据 HTTP 地址推算 WebSocket 地址 (http -> ws, https -> wss)
const WS_BASE_URL = API_BASE_URL.replace(/^http/, 'ws')

export async function createSession(): Promise<Session> {
  const response = await fetch(`${API_BASE_URL}/sessions/`, {
    method: 'POST'
  })
  if (!response.ok) {
    throw new Error('Failed to create session')
  }
  return response.json()
}

export async function getSession(sessionId: string): Promise<Session> {
  const response = await fetch(`${API_BASE_URL}/sessions/${sessionId}`)
  if (!response.ok) {
    throw new Error('Failed to get session')
  }
  return response.json()
}

export function getWebSocketUrl(sessionId: string): string {
  return `${WS_BASE_URL}/ws/${sessionId}`
}

export async function deleteSession(sessionId: string): Promise<void> {
  console.warn('后端暂未实现删除接口，仅在前端清除。')
  // 预留接口位置
}

export type { Message, Session as ChatSession }