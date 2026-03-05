/**
 * Mock API service – used when VITE_MOCK_MODE=true.
 *
 * Provides in-memory implementations of all backend API calls and a
 * MockWebSocket class that simulates server-sent AI responses so the
 * frontend can be developed and demonstrated without a running backend.
 */

// ---------------------------------------------------------------------------
// In-memory session store
// ---------------------------------------------------------------------------

interface MockSession {
  id: string
  created_at: string
  messages: MockMessage[]
}

interface MockMessage {
  id: number
  session_id: string
  role: string
  content: string
  message_type: string
  media_url: string | null
  citations: string | null
  created_at: string
  feedback_score: number | null
}

const _sessions: Record<string, MockSession> = {}
let _messageIdCounter = 1

// ---------------------------------------------------------------------------
// Canned AI responses (rotated round-robin)
// ---------------------------------------------------------------------------

const _mockResponses = [
  '根据《民法典》相关规定，您描述的情况属于常见民事纠纷。建议您保存好相关证据（合同、转账记录、聊天记录等），并向当地人民法院提起诉讼。如金额较小（5000元以下），可走小额诉讼程序，更为便捷高效。',
  '您好！根据《劳动合同法》第四十七条，劳动者工作每满一年应支付一个月工资的经济补偿。公司无故辞退属于违法解除，您有权要求双倍经济补偿（即赔偿金）。建议您在离职后一年内向劳动仲裁委员会申请仲裁。',
  '根据最高法关于民间借贷的司法解释，民间借贷的诉讼时效为三年，从权利人知道或应当知道权利被侵害之日起计算。超过三年未主张权利，法院将不予支持，但对方自愿履行的除外。',
  '房屋租赁合同中常见风险包括：(1) 出租人非产权人或无授权；(2) 未约定维修责任；(3) 押金退还条款模糊；(4) 提前解约违约金过高。建议签约前核实房产证及产权人身份，并将口头承诺写入合同。',
  '根据《消费者权益保护法》第二十五条，经营者采用网络、电视、电话、邮购等方式销售商品，消费者有权自收到商品之日起七日内退货，且无需说明理由（"七天无理由退货"）。',
]

let _responseIndex = 0

function _nextMockResponse(): string {
  const r = _mockResponses[_responseIndex % _mockResponses.length]
  _responseIndex++
  return r
}

// ---------------------------------------------------------------------------
// Mock REST helpers
// ---------------------------------------------------------------------------

export function mockCreateSession(): MockSession {
  const id = 'mock-' + Date.now().toString(36)
  const session: MockSession = { id, created_at: new Date().toISOString(), messages: [] }
  _sessions[id] = session
  return session
}

export function mockGetSessions(): MockSession[] {
  return Object.values(_sessions)
}

export function mockGetSession(sessionId: string): MockSession {
  if (!_sessions[sessionId]) {
    _sessions[sessionId] = { id: sessionId, created_at: new Date().toISOString(), messages: [] }
  }
  return _sessions[sessionId]
}

export function mockLoginUser(_username: string, _password: string): { access_token: string; token_type: string } {
  return { access_token: 'mock-token-' + Date.now(), token_type: 'bearer' }
}

export function mockRegisterUser(_user: { username: string; password: string }): {
  access_token: string
  token_type: string
} {
  return { access_token: 'mock-token-' + Date.now(), token_type: 'bearer' }
}

// ---------------------------------------------------------------------------
// MockWebSocket
//
// Implements the subset of the WebSocket API that ChatWindow.vue uses:
//   • readyState, onopen, onclose, onmessage, onerror
//   • send(), close()
//   • static OPEN / CLOSED constants
// ---------------------------------------------------------------------------

export class MockWebSocket {
  static readonly CONNECTING = 0
  static readonly OPEN = 1
  static readonly CLOSING = 2
  static readonly CLOSED = 3

  readyState: number = MockWebSocket.CONNECTING

  onopen: ((event: Event) => void) | null = null
  onclose: ((event: CloseEvent) => void) | null = null
  onmessage: ((event: MessageEvent) => void) | null = null
  onerror: ((event: Event) => void) | null = null

  private _sessionId: string

  constructor(url: string) {
    // Extract session id from ws://host/ws/<sessionId>
    this._sessionId = url.split('/').pop() ?? 'unknown'

    // Simulate async connection handshake
    setTimeout(() => {
      this.readyState = MockWebSocket.OPEN
      this.onopen?.(new Event('open'))
    }, 80)
  }

  send(data: string): void {
    if (this.readyState !== MockWebSocket.OPEN) return

    try {
      const payload = JSON.parse(data) as { content?: string; type?: string }

      // Persist the user message first (gets the next sequential ID)
      const session = _sessions[this._sessionId]
      if (session && payload.content) {
        session.messages.push({
          id: _messageIdCounter++,
          session_id: this._sessionId,
          role: 'user',
          content: payload.content,
          message_type: payload.type ?? 'text',
          media_url: null,
          citations: null,
          created_at: new Date().toISOString(),
          feedback_score: null,
        })
      }

      // Simulate network + AI processing delay (600–1200 ms)
      const delay = 600 + Math.floor(Math.random() * 600)
      setTimeout(() => {
        if (this.readyState !== MockWebSocket.OPEN) return

        const messageId = _messageIdCounter++
        const aiContent = _nextMockResponse()

        // Persist assistant message in the mock session store
        if (session) {
          session.messages.push({
            id: messageId,
            session_id: this._sessionId,
            role: 'assistant',
            content: aiContent,
            message_type: 'text',
            media_url: null,
            citations: '【模拟模式 - 仅供演示，不代表真实法律意见】',
            created_at: new Date().toISOString(),
            feedback_score: null,
          })
        }

        const response = {
          role: 'assistant',
          content: aiContent,
          type: 'text',
          mediaUrl: null,
          citations: '【模拟模式 - 仅供演示，不代表真实法律意见】',
          messageId,
        }
        this.onmessage?.(new MessageEvent('message', { data: JSON.stringify(response) }))
      }, delay)
    } catch (err) {
      console.error('[MockWebSocket] Failed to parse outgoing message:', err)
    }
  }

  close(): void {
    this.readyState = MockWebSocket.CLOSED
    this.onclose?.(new CloseEvent('close', { wasClean: true, code: 1000 }))
  }
}
