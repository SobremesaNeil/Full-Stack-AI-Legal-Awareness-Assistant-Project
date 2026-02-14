export interface Message {
  role: 'user' | 'assistant'
  content: string
  created_at?: string
}

export interface ChatMessage {
  role: 'user' | 'assistant'
  content: string
}

export interface ChatSession {
  session_id: string
  created_at: string
  messages: Message[]
  context: ChatMessage[]
  label?: string
}

export interface WebSocketMessage {
  content: string
  context: ChatMessage[]
}

export interface DialogOptions {
  title: string
  text: string
  confirmText?: string
  cancelText?: string
  type?: 'info' | 'warning' | 'error'
}

export interface SnackbarOptions {
  text: string
  color?: 'success' | 'error' | 'warning' | 'info'
  timeout?: number
}

export interface ChatState {
  messages: Message[]
  context: ChatMessage[]
  loading: boolean
  sessionId: string | null
  sessions: ChatSession[]
  currentSessionId: string
} 
