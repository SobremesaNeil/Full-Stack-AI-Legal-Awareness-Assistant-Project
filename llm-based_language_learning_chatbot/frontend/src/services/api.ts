// 1. 引入统一的类型定义 (确保和 types/chat.ts 保持一致)
import type { Message, Session } from '@/types/chat'

// 2. 配置后端地址
// 如果您的 vite.config.ts 没有配置 proxy，建议直接写死后端地址
// 后端 main.py 已经配置了 CORS 允许跨域，所以这样写最稳妥
const API_BASE_URL = 'http://localhost:8000'
const WS_BASE_URL = 'ws://localhost:8000'

// 3. 创建会话
export async function createSession(): Promise<Session> {
  const response = await fetch(`${API_BASE_URL}/sessions/`, {
    method: 'POST'
  })
  if (!response.ok) {
    throw new Error('Failed to create session')
  }
  return response.json()
}

// 4. 获取会话详情
export async function getSession(sessionId: string): Promise<Session> {
  const response = await fetch(`${API_BASE_URL}/sessions/${sessionId}`)
  if (!response.ok) {
    throw new Error('Failed to get session')
  }
  // 后端返回的数据可能包含 snake_case (下划线)，这里可能需要转换，
  // 但我们在 ChatWindow.vue 里已经做了兼容处理，所以直接返回即可
  return response.json()
}

// 5. 获取 WebSocket 连接地址
export function getWebSocketUrl(sessionId: string): string {
  // 直接拼接，简单粗暴且有效
  return `${WS_BASE_URL}/ws/${sessionId}`
}

// 6. 删除会话 (注意：后端 main.py 还没写 DELETE 接口，暂时注释掉报错逻辑)
export async function deleteSession(sessionId: string): Promise<void> {
  console.warn('后端暂未实现删除接口，仅在前端清除。')
  
  // 等后端实现了 @app.delete("/sessions/{session_id}") 后再解开下面代码:
  /*
  const response = await fetch(`${API_BASE_URL}/sessions/${sessionId}`, {
    method: 'DELETE'
  })
  if (!response.ok) {
    throw new Error('Failed to delete session')
  }
  */
}

// 为了兼容旧代码引用，如果其他文件还在引用这些类型，可以重新导出
export type { Message, Session as ChatSession }