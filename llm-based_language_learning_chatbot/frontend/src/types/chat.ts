export interface Message {
  id?: number;
  role: 'user' | 'assistant';
  content: string;
  type: 'text' | 'image' | 'audio' | 'mindmap'; // 新增类型
  mediaUrl?: string; // 媒体文件链接
  created_at?: string;
}

export interface Session {
  id: string;
  created_at: string;
  messages: Message[];
}