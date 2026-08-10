class MockWebSocket {
  static instances: MockWebSocket[] = []
  onmessage: ((ev: { data: string }) => void) | null = null
  onclose: (() => void) | null = null
  onopen: (() => void) | null = null
  onerror: (() => void) | null = null
  readyState = 1

  constructor(public url: string) {
    MockWebSocket.instances.push(this)
  }

  send(_data: string): void {}
  close(): void {}
}

Object.defineProperty(globalThis, 'WebSocket', {
  writable: true,
  value: MockWebSocket,
})

if (!Element.prototype.scrollIntoView) {
  Element.prototype.scrollIntoView = () => {}
}

export {}
