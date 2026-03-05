import { describe, it, expect, vi, beforeEach } from 'vitest'
import {
  MockWebSocket,
  mockCreateSession,
  mockGetSessions,
  mockGetSession,
  mockLoginUser,
  mockRegisterUser,
} from '../mockApi'

// ---------------------------------------------------------------------------
// Mock REST helpers
// ---------------------------------------------------------------------------

describe('mockCreateSession', () => {
  it('returns a session with a unique id and empty messages', () => {
    const s = mockCreateSession()
    expect(s.id).toMatch(/^mock-/)
    expect(s.messages).toEqual([])
    expect(s.created_at).toBeTruthy()
  })

  it('each call returns a different id', () => {
    const a = mockCreateSession()
    const b = mockCreateSession()
    expect(a.id).not.toBe(b.id)
  })
})

describe('mockGetSessions', () => {
  it('includes sessions created via mockCreateSession', () => {
    const s = mockCreateSession()
    const all = mockGetSessions()
    expect(all.some((x) => x.id === s.id)).toBe(true)
  })
})

describe('mockGetSession', () => {
  it('returns the session that was created', () => {
    const s = mockCreateSession()
    const fetched = mockGetSession(s.id)
    expect(fetched.id).toBe(s.id)
  })

  it('auto-creates a session for an unknown id', () => {
    const fetched = mockGetSession('unknown-xyz')
    expect(fetched.id).toBe('unknown-xyz')
  })
})

describe('mockLoginUser', () => {
  it('returns an access token', () => {
    const result = mockLoginUser('admin', 'password')
    expect(result.access_token).toMatch(/^mock-token-/)
    expect(result.token_type).toBe('bearer')
  })
})

describe('mockRegisterUser', () => {
  it('returns an access token', () => {
    const result = mockRegisterUser({ username: 'test', password: 'Test1234' })
    expect(result.access_token).toMatch(/^mock-token-/)
    expect(result.token_type).toBe('bearer')
  })
})

// ---------------------------------------------------------------------------
// MockWebSocket
// ---------------------------------------------------------------------------

describe('MockWebSocket', () => {
  it('fires onopen asynchronously after construction', () =>
    new Promise<void>((resolve) => {
      const ws = new MockWebSocket('ws://localhost/ws/test-session')
      expect(ws.readyState).toBe(MockWebSocket.CONNECTING)
      ws.onopen = () => {
        expect(ws.readyState).toBe(MockWebSocket.OPEN)
        resolve()
      }
    }))

  it('fires onmessage with a JSON assistant response after send()', () =>
    new Promise<void>((resolve) => {
      const session = mockCreateSession()
      const ws = new MockWebSocket(`ws://localhost/ws/${session.id}`)
      ws.onopen = () => {
        ws.onmessage = (event) => {
          const data = JSON.parse(event.data)
          expect(data.role).toBe('assistant')
          expect(typeof data.content).toBe('string')
          expect(data.content.length).toBeGreaterThan(0)
          expect(data.type).toBe('text')
          resolve()
        }
        ws.send(JSON.stringify({ content: '朋友借钱不还怎么办？', type: 'text' }))
      }
    }))

  it('sets readyState to CLOSED after close()', () =>
    new Promise<void>((resolve) => {
      const ws = new MockWebSocket('ws://localhost/ws/test-session')
      ws.onopen = () => {
        ws.close()
        expect(ws.readyState).toBe(MockWebSocket.CLOSED)
        resolve()
      }
    }))

  it('fires onclose after close()', () =>
    new Promise<void>((resolve) => {
      const ws = new MockWebSocket('ws://localhost/ws/test-session')
      ws.onopen = () => {
        ws.onclose = () => resolve()
        ws.close()
      }
    }))
})
