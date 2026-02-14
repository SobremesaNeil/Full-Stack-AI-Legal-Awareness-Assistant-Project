const SESSION_ID_KEY = 'chat_session_id'

export function saveSessionId(sessionId: string): void {
  localStorage.setItem(SESSION_ID_KEY, sessionId)
}

export function getSessionId(): string | null {
  return localStorage.getItem(SESSION_ID_KEY)
}

export function clearSessionId(): void {
  localStorage.removeItem(SESSION_ID_KEY)
} 