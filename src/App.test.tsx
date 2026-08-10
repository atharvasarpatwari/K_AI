import { describe, expect, it, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import App from './App'

const baseState = {
  system: {
    cpu: 42,
    cores: 8,
    memoryUsed: 8 * 1024 ** 3,
    memoryTotal: 16 * 1024 ** 3,
    memoryPercent: 50,
    diskUsed: 100 * 1024 ** 3,
    diskTotal: 200 * 1024 ** 3,
    diskPercent: 50,
    batteryPercent: 80,
    batteryCharging: true,
    uptime: 300,
    platform: 'Windows',
    hostname: 'test-pc',
    python: '3.13',
  },
  processes: [
    { pid: 1234, name: 'chrome', cpu: 90, memory: 20 },
    { pid: 5678, name: 'python', cpu: 5, memory: 1.5 },
  ],
  tasks: [],
  timers: [],
}

function mockFetch(chatResponse: Record<string, unknown>): void {
  const fetchMock = vi.fn((url: RequestInfo | URL, init?: RequestInit) => {
    const path = String(url)
    if (path.startsWith('/api/state')) {
      return Promise.resolve({ ok: true, json: () => Promise.resolve(baseState) })
    }
    if (path.startsWith('/api/files')) {
      return Promise.resolve({
        ok: true,
        json: () => Promise.resolve({ path: 'C:\\', entries: [] }),
      })
    }
    if (path === '/api/chat') {
      return Promise.resolve({ ok: true, json: () => Promise.resolve(chatResponse) })
    }
    if (path === '/api/confirm') {
      return Promise.resolve({ ok: true, json: () => Promise.resolve(chatResponse) })
    }
    if (path === '/api/action') {
      return Promise.resolve({ ok: true, json: () => Promise.resolve(chatResponse) })
    }
    if (path === '/api/transcribe') {
      return Promise.resolve({
        ok: true,
        json: () => Promise.resolve({ text: 'turn on the light' }),
      })
    }
    if (path === '/api/reset') {
      return Promise.resolve({ ok: true, json: () => Promise.resolve({ ok: true }) })
    }
    return Promise.reject(new Error(`Unhandled fetch: ${path}`))
  })
  vi.stubGlobal('fetch', fetchMock)
}

describe('App', () => {
  it('renders the initial empty state', async () => {
    mockFetch({})
    render(<App />)
    expect(
      await screen.findByText(/Ask KEERTHI to check CPU usage/),
    ).toBeTruthy()
  })

  it('sends a message and shows the reply', async () => {
    mockFetch({
      reply: 'Reading system status. [ACTION:CPU_USAGE]',
      actions: ['CPU usage is 42%'],
      state: baseState,
      needsConfirmation: false,
    })
    const user = userEvent.setup()
    render(<App />)
    await user.type(screen.getByPlaceholderText('Type a message…'), 'status')
    await user.click(screen.getByRole('button', { name: /Send/ }))
    expect(await screen.findByText('status')).toBeTruthy()
    expect(await screen.findByText(/Reading system status/)).toBeTruthy()
  })

  it('shows confirm prompt for safety actions and confirms via /api/confirm', async () => {
    const fetchMock = vi.fn((url: RequestInfo | URL, _init?: RequestInit) => {
      const path = String(url)
      if (path.startsWith('/api/state')) {
        return Promise.resolve({ ok: true, json: () => Promise.resolve(baseState) })
      }
      if (path.startsWith('/api/files')) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({ path: 'C:\\', entries: [] }),
        })
      }
      if (path === '/api/chat') {
        return Promise.resolve({
          ok: true,
          json: () =>
            Promise.resolve({
              reply: 'Killing the process. [ACTION:KILL_PROCESS:1234]',
              actions: [],
              state: baseState,
              needsConfirmation: true,
              confirmationToken: 'abc123',
              pendingIntents: ['KILL_PROCESS'],
            }),
        })
      }
      if (path === '/api/confirm') {
        return Promise.resolve({
          ok: true,
          json: () =>
            Promise.resolve({
              reply: 'Killing the process. [ACTION:KILL_PROCESS:1234]',
              actions: ['Terminated chrome (PID 1234).'],
              state: baseState,
              needsConfirmation: false,
            }),
        })
      }
      if (path === '/api/reset') {
        return Promise.resolve({ ok: true, json: () => Promise.resolve({ ok: true }) })
      }
      return Promise.reject(new Error(`Unhandled fetch: ${path}`))
    })
    vi.stubGlobal('fetch', fetchMock)

    const user = userEvent.setup()
    render(<App />)
    await user.type(screen.getByPlaceholderText('Type a message…'), 'kill chrome')
    await user.click(screen.getByRole('button', { name: /Send/ }))
    await user.click(await screen.findByRole('button', { name: /Confirm & proceed/ }))

    const confirmCall = fetchMock.mock.calls.find(([url]) => String(url) === '/api/confirm')
    expect(confirmCall).toBeTruthy()
    expect(String(confirmCall?.[1]?.body)).toContain('abc123')
    expect(
      screen.queryByRole('button', { name: /Confirm & proceed/ }),
    ).toBeNull()
  })

  it('shows live system gauges and process list', async () => {
    mockFetch({})
    render(<App />)
    expect(await screen.findByText('test-pc')).toBeTruthy()
    expect(await screen.findByText('42')).toBeTruthy()
    expect(await screen.findByText('80')).toBeTruthy()
    expect((await screen.findAllByText('chrome')).length).toBeGreaterThan(0)
    expect(await screen.findByText('90%')).toBeTruthy()
  })

  it('opens an app via /api/action', async () => {
    const fetchMock = vi.fn((url: RequestInfo | URL, init?: RequestInit) => {
      const path = String(url)
      if (path.startsWith('/api/state')) {
        return Promise.resolve({ ok: true, json: () => Promise.resolve(baseState) })
      }
      if (path.startsWith('/api/files')) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({ path: 'C:\\', entries: [] }),
        })
      }
      if (path === '/api/action') {
        return Promise.resolve({
          ok: true,
          json: () =>
            Promise.resolve({
              reply: '',
              actions: ['Opened notepad.'],
              state: baseState,
              needsConfirmation: false,
            }),
        })
      }
      return Promise.reject(new Error(`Unhandled fetch: ${path}`))
    })
    vi.stubGlobal('fetch', fetchMock)

    const user = userEvent.setup()
    render(<App />)
    await user.click(await screen.findByRole('button', { name: /Open selected app/ }))

    const actionCall = fetchMock.mock.calls.find(([url]) => String(url) === '/api/action')
    expect(actionCall).toBeTruthy()
    expect(String(actionCall?.[1]?.body)).toContain('OPEN_APP')
    expect(String(actionCall?.[1]?.body)).toContain('notepad')
    expect(await screen.findByText('Opened notepad.')).toBeTruthy()
  })

  it('shows live timer countdowns', async () => {
    const stateWithTimer = {
      system: baseState.system,
      processes: baseState.processes,
      tasks: [],
      timers: [{ label: 'Pasta', due: Date.now() / 1000 + 90 }],
    }
    const fetchMock = vi.fn((url: RequestInfo | URL) => {
      const path = String(url)
      if (path.startsWith('/api/state')) {
        return Promise.resolve({ ok: true, json: () => Promise.resolve(stateWithTimer) })
      }
      if (path.startsWith('/api/files')) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({ path: 'C:\\', entries: [] }),
        })
      }
      return Promise.reject(new Error(`Unhandled fetch: ${path}`))
    })
    vi.stubGlobal('fetch', fetchMock)

    render(<App />)
    expect(await screen.findByText('Pasta')).toBeTruthy()
    expect(await screen.findByText(/1m \d+s/)).toBeTruthy()
  })

  it('records mic audio, transcribes it, and auto-sends it', async () => {
    const track = { stop: vi.fn() }
    const stream = { getTracks: () => [track] }
    Object.defineProperty(navigator, 'mediaDevices', {
      value: { getUserMedia: vi.fn().mockResolvedValue(stream) },
      configurable: true,
    })

    class MockRecorder {
      mimeType = 'audio/webm'
      ondataavailable: ((e: { data: Blob }) => void) | null = null
      onstop: (() => void) | null = null
      start() {}
      stop() {
        this.ondataavailable?.({ data: new Blob(['fake']) })
        this.onstop?.()
      }
    }
    vi.stubGlobal('MediaRecorder', MockRecorder)

    class MockAudioBuffer {
      sampleRate = 16000
      duration = 1
      getChannelData() {
        return new Float32Array(16000)
      }
    }
    class MockAudioContext {
      sampleRate = 48000
      decodeAudioData() {
        return Promise.resolve(new MockAudioBuffer())
      }
      close() {
        return Promise.resolve()
      }
    }
    class MockOfflineAudioContext {
      destination = {}
      createBufferSource() {
        return { buffer: null, connect() {}, start() {} }
      }
      startRendering() {
        return Promise.resolve(new MockAudioBuffer())
      }
    }
    vi.stubGlobal('AudioContext', MockAudioContext)
    vi.stubGlobal('OfflineAudioContext', MockOfflineAudioContext)

    const fetchMock = vi.fn((url: RequestInfo | URL, init?: RequestInit) => {
      const path = String(url)
      if (path.startsWith('/api/state')) {
        return Promise.resolve({ ok: true, json: () => Promise.resolve(baseState) })
      }
      if (path.startsWith('/api/files')) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({ path: 'C:\\', entries: [] }),
        })
      }
      if (path === '/api/transcribe') {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({ text: 'turn on the light' }),
        })
      }
      if (path === '/api/chat') {
        return Promise.resolve({
          ok: true,
          json: () =>
            Promise.resolve({
              reply: 'Reading system status. [ACTION:CPU_USAGE]',
              actions: ['CPU usage is 42%'],
              state: baseState,
              needsConfirmation: false,
            }),
        })
      }
      return Promise.reject(new Error(`Unhandled fetch: ${path}`))
    })
    vi.stubGlobal('fetch', fetchMock)

    const user = userEvent.setup()
    render(<App />)
    await user.click(await screen.findByRole('button', { name: /Mic/ }))
    await user.click(await screen.findByRole('button', { name: /Recording/ }))

    expect(await screen.findByText('turn on the light')).toBeTruthy()
    expect(await screen.findByText(/Reading system status/)).toBeTruthy()
    const transcribeCall = fetchMock.mock.calls.find(
      ([url]) => String(url) === '/api/transcribe',
    )
    expect(transcribeCall).toBeTruthy()
    expect(transcribeCall?.[1]?.body ?? null).toBeInstanceOf(ArrayBuffer)
    const chatCall = fetchMock.mock.calls.find(([url]) => String(url) === '/api/chat')
    expect(chatCall).toBeTruthy()
    expect(String(chatCall?.[1]?.body)).toContain('turn on the light')
  })
})
