export interface Message {
  role: 'user' | 'assistant' | 'system'
  content: string
  type?: 'text' | 'image' | 'audio' | 'mindmap'
  media_url?: string
  citations?: string // RAG 引用
  messageId?: number // 用于反馈
  created_at?: string // <--- 新增这一行，解决报错
}

export interface Session {
  id: string
  messages: Message[]
  created_at: string
}