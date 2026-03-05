import { useAuthStore } from '@/stores/auth'
import {
  MockWebSocket,
  mockCreateSession,
  mockGetSessions,
  mockGetSession,
  mockLoginUser,
  mockRegisterUser,
} from './mockApi'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

// When VITE_MOCK_MODE=true the frontend runs fully offline (no backend needed).
// Start the dev server with: npm run dev:mock
const MOCK_MODE = import.meta.env.VITE_MOCK_MODE === 'true'

// Fix WebSocket protocol: http/https -> ws/wss
const WS_BASE_URL = API_BASE_URL.replace(/^https?/, (match) => {
  return match === 'https' ? 'wss' : 'ws'
})

// 辅助函数：带 Token 的 Fetch
async function authFetch(url: string, options: RequestInit = {}) {
  const authStore = useAuthStore()
  const headers = new Headers(options.headers)
  
  if (authStore.token) {
    headers.append('Authorization', `Bearer ${authStore.token}`)
  }

  const response = await fetch(`${API_BASE_URL}${url}`, {
    ...options,
    headers
  })

  if (response.status === 401) {
    authStore.logout()
    throw new Error('登录已过期，请重新登录')
  }
  
  return response
}

// --- Auth ---
export async function loginUser(username: string, password: string) {
  if (MOCK_MODE) return mockLoginUser(username, password)

  const formData = new URLSearchParams()
  formData.append('username', username)
  formData.append('password', password)

  const response = await fetch(`${API_BASE_URL}/token`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    body: formData
  })
  if (!response.ok) throw new Error('登录失败')
  return response.json() // returns { access_token, token_type }
}

export async function registerUser(user: any) {
  if (MOCK_MODE) return mockRegisterUser(user)

  const response = await fetch(`${API_BASE_URL}/register`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(user)
  })
  if (!response.ok) throw new Error('注册失败，用户名可能已存在')
  return response.json()
}

// --- Chat & Session ---
export async function createSession() {
  if (MOCK_MODE) return mockCreateSession()

  const response = await fetch(`${API_BASE_URL}/sessions/`, { method: 'POST' })
  return response.json()
}

export async function getSessions() {
  if (MOCK_MODE) return mockGetSessions()

  const response = await fetch(`${API_BASE_URL}/sessions/`)
  if (!response.ok) throw new Error('Failed to load sessions')
  return response.json()
}

export async function getSession(sessionId: string) {
  if (MOCK_MODE) return mockGetSession(sessionId)

  const response = await fetch(`${API_BASE_URL}/sessions/${sessionId}`)
  return response.json()
}

export function getWebSocketUrl(sessionId: string): string {
  return `${WS_BASE_URL}/ws/${sessionId}`
}

/**
 * Factory that returns either a real WebSocket or a MockWebSocket depending
 * on whether VITE_MOCK_MODE is enabled.  Use this instead of `new WebSocket()`
 * so that the mock can intercept connections without requiring a backend.
 */
export function createWebSocket(url: string): WebSocket {
  if (MOCK_MODE) {
    return new MockWebSocket(url) as unknown as WebSocket
  }
  return new WebSocket(url)
}

// --- Feedback ---
export async function submitFeedback(messageId: number, score: number) {
  if (MOCK_MODE) return Promise.resolve({ status: 'success' })

  // 反馈通常不需要强制登录，但如果有 Token 最好带上
  return authFetch('/feedback/', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ message_id: messageId, score })
  })
}

// --- Tickets (付费/专家咨询) ---
export async function createTicket(ticket: { title: string, description: string }) {
  const response = await authFetch('/tickets/', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(ticket)
  })
  if (!response.ok) throw new Error('提交工单失败')
  return response.json()
}

export async function getAdminTickets() {
  const response = await authFetch('/admin/tickets')
  if (!response.ok) throw new Error('获取工单失败')
  return response.json()
}

export async function replyTicket(ticketId: number, reply: string) {
  const response = await authFetch(`/admin/tickets/${ticketId}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ expert_reply: reply, status: 'answered' })
  })
  if (!response.ok) throw new Error('回复失败')
  return response.json()
}

// --- Rules (专家规则库 / 规则引擎) [新增] ---
export async function getRules() {
  const response = await authFetch('/admin/rules')
  if (!response.ok) throw new Error('获取规则库失败')
  return response.json()
}

export async function createRule(rule: { patterns: string[], answer: string, source: string, active: boolean }) {
  const response = await authFetch('/admin/rules', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(rule)
  })
  if (!response.ok) throw new Error('创建规则失败')
  return response.json()
}

export async function deleteRule(ruleId: number) {
  const response = await authFetch(`/admin/rules/${ruleId}`, {
    method: 'DELETE'
  })
  if (!response.ok) throw new Error('删除规则失败')
  return response.json()
}

// --- File Upload ---
export async function uploadFile(file: File) {
  const formData = new FormData()
  formData.append('file', file)
  const response = await fetch(`${API_BASE_URL}/upload/`, {
    method: 'POST',
    body: formData
  })
  if (!response.ok) throw new Error('文件上传失败')
  return response.json()
}