import { useAuthStore } from '@/stores/auth'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'
const WS_BASE_URL = API_BASE_URL.replace(/^http/, 'ws')

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
  const response = await fetch(`${API_BASE_URL}/sessions/`, { method: 'POST' })
  return response.json()
}

export async function getSession(sessionId: string) {
  const response = await fetch(`${API_BASE_URL}/sessions/${sessionId}`)
  return response.json()
}

export function getWebSocketUrl(sessionId: string): string {
  return `${WS_BASE_URL}/ws/${sessionId}`
}

// --- Feedback ---
export async function submitFeedback(messageId: number, score: number) {
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