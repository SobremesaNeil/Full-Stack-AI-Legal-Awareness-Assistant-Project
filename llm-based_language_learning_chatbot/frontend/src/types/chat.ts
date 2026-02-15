export interface Message {
  role: 'user' | 'assistant' | 'system'
  content: string
  type?: 'text' | 'image' | 'audio' | 'mindmap'
  media_url?: string
  citations?: string // RAG 引用
  messageId?: number // 用于反馈
}

export interface Session {
  id: string
  messages: Message[]
  created_at: string
}