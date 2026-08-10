import { describe, expect, it, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import App from './App'

const baseState = {
  devices: { living_room_light: { status: 'off' } },
  tasks: [],
  timers: [],
}

function mockFetch(chatResponse: Record<string, unknown>): void {
  const fetchMock = vi.fn((url: RequestInfo | URL) => {
    const path = String(url)
    if (path === '/api/state') {
      return Promise.resolve({ ok: true, json: () => Promise.resolve(baseState) })
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
      await screen.findByText(/Ask KEERTHI to turn on the lights/),
    ).toBeTruthy()
  })

  it('sends a message and shows the reply', async () => {
    mockFetch({
      reply: 'Turning on the light. [ACTION:LIGHT_ON]',
      actions: ['Living room light: ACTIVE'],
      state: baseState,
      needsConfirmation: false,
    })
    const user = userEvent.setup()
    render(<App />)
    await user.type(screen.getByPlaceholderText('Type a message…'), 'lights on')
    await user.click(screen.getByRole('button', { name: /Send/ }))
    expect(await screen.findByText('lights on')).toBeTruthy()
    expect(await screen.findByText(/Turning on the light/)).toBeTruthy()
  })

  it('shows confirm prompt for safety actions and confirms via /api/confirm', async () => {
    const fetchMock = vi.fn((url: RequestInfo | URL, _init?: RequestInit) => {
      const path = String(url)
      if (path === '/api/state') {
        return Promise.resolve({ ok: true, json: () => Promise.resolve(baseState) })
      }
      if (path === '/api/chat') {
        return Promise.resolve({
          ok: true,
          json: () =>
            Promise.resolve({
              reply: 'Unlocking the door. [ACTION:UNLOCK_DOOR]',
              actions: [],
              state: baseState,
              needsConfirmation: true,
              confirmationToken: 'abc123',
              pendingIntents: ['UNLOCK_DOOR'],
            }),
        })
      }
      if (path === '/api/confirm') {
        return Promise.resolve({
          ok: true,
          json: () =>
            Promise.resolve({
              reply: 'Unlocking the door. [ACTION:UNLOCK_DOOR]',
              actions: ['Main entrance: UNLOCKED'],
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
    await user.type(screen.getByPlaceholderText('Type a message…'), 'unlock the door')
    await user.click(screen.getByRole('button', { name: /Send/ }))
    await user.click(await screen.findByRole('button', { name: /Confirm & proceed/ }))

    const confirmCall = fetchMock.mock.calls.find(([url]) => String(url) === '/api/confirm')
    expect(confirmCall).toBeTruthy()
    expect(String(confirmCall?.[1]?.body)).toContain('abc123')
    expect(
      screen.queryByRole('button', { name: /Confirm & proceed/ }),
    ).toBeNull()
  })

  it('toggles a device via /api/action', async () => {
    const fetchMock = vi.fn((url: RequestInfo | URL, init?: RequestInit) => {
      const path = String(url)
      if (path === '/api/state') {
        return Promise.resolve({ ok: true, json: () => Promise.resolve(baseState) })
      }
      if (path === '/api/action') {
        const body = String(init?.body ?? '')
        const on = body.includes('LIGHT_ON')
        return Promise.resolve({
          ok: true,
          json: () =>
            Promise.resolve({
              reply: '',
              actions: [`Living room light: ${on ? 'ACTIVE' : 'OFF'}`],
              state: {
                devices: { living_room_light: { status: on ? 'on' : 'off' } },
                tasks: [],
                timers: [],
              },
              needsConfirmation: false,
            }),
        })
      }
      return Promise.reject(new Error(`Unhandled fetch: ${path}`))
    })
    vi.stubGlobal('fetch', fetchMock)

    const user = userEvent.setup()
    render(<App />)
    await user.click(await screen.findByRole('button', { name: 'OFF' }))

    const actionCall = fetchMock.mock.calls.find(([url]) => String(url) === '/api/action')
    expect(actionCall).toBeTruthy()
    expect(String(actionCall?.[1]?.body)).toContain('LIGHT_ON')
    expect(await screen.findByRole('button', { name: 'ON' })).toBeTruthy()
  })

  it('shows live timer countdowns', async () => {
    const stateWithTimer = {
      devices: {},
      tasks: [],
      timers: [{ label: 'Pasta', due: Date.now() / 1000 + 90 }],
    }
    const fetchMock = vi.fn((url: RequestInfo | URL) => {
      const path = String(url)
      if (path === '/api/state') {
        return Promise.resolve({ ok: true, json: () => Promise.resolve(stateWithTimer) })
      }
      return Promise.reject(new Error(`Unhandled fetch: ${path}`))
    })
    vi.stubGlobal('fetch', fetchMock)

    render(<App />)
    expect(await screen.findByText('Pasta')).toBeTruthy()
    expect(await screen.findByText(/1m \d+s/)).toBeTruthy()
  })
})
