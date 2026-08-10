import { useEffect, useRef, useState } from 'react'
import Markdown from 'react-markdown'
import { Bot, Power, RefreshCw, Send, User } from 'lucide-react'

type DeviceInfo = {
  status: string
  brightness?: number
  temp?: number
  speed?: number
}

type ApiState = {
  devices: Record<string, DeviceInfo>
  tasks: string[]
  timers: { label: string; due: number }[]
}

type ChatResponse = {
  reply: string
  actions: string[]
  state: ApiState
  needsConfirmation: boolean
}

type Message = {
  role: 'user' | 'assistant'
  content: string
}

async function postChat(message: string, confirmed = false): Promise<ChatResponse> {
  const res = await fetch('/api/chat', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ message, confirmed }),
  })
  if (!res.ok) {
    throw new Error(`Request failed with status ${res.status}`)
  }
  return res.json()
}

async function fetchState(): Promise<ApiState> {
  const res = await fetch('/api/state')
  if (!res.ok) {
    throw new Error(`Request failed with status ${res.status}`)
  }
  return res.json()
}

export default function App() {
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [state, setState] = useState<ApiState | null>(null)
  const [loading, setLoading] = useState(false)
  const [pendingConfirm, setPendingConfirm] = useState<string | null>(null)
  const endRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    fetchState().then(setState).catch(() => undefined)
  }, [])

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, loading])

  async function handleSend(confirmed = false) {
    const message = pendingConfirm ?? input.trim()
    if (!message || loading) return
    setLoading(true)
    setInput('')
    setPendingConfirm(null)

    const userMessage: Message = { role: 'user', content: message }
    setMessages((prev) => [...prev, userMessage])

    try {
      const result = await postChat(message, confirmed)
      setMessages((prev) => [...prev, { role: 'assistant', content: result.reply }])
      setState(result.state)
      if (result.needsConfirmation) {
        setPendingConfirm(message)
      }
    } catch {
      setMessages((prev) => [
        ...prev,
        { role: 'assistant', content: 'I hit a technical snag. Please try again.' },
      ])
    } finally {
      setLoading(false)
    }
  }

  async function handleReset() {
    await fetch('/api/reset', { method: 'POST' })
    setMessages([])
    fetchState().then(setState).catch(() => undefined)
  }

  return (
    <div className="flex h-screen bg-slate-950 text-slate-100">
      <main className="flex flex-1 flex-col">
        <header className="flex items-center gap-3 border-b border-slate-800 px-6 py-4">
          <Bot className="h-6 w-6 text-cyan-400" />
          <h1 className="text-lg font-semibold">KEERTHI</h1>
          <span className="text-xs text-slate-400">AI Voice Assistant</span>
          <button
            onClick={handleReset}
            className="ml-auto inline-flex items-center gap-2 rounded-md border border-slate-700 px-3 py-1.5 text-sm hover:bg-slate-800"
            title="Clear conversation"
          >
            <RefreshCw className="h-4 w-4" /> Reset
          </button>
        </header>

        <section className="flex-1 space-y-4 overflow-y-auto px-6 py-4">
          {messages.length === 0 && (
            <p className="pt-16 text-center text-slate-500">
              Ask KEERTHI to turn on the lights, set a timer, or check the weather.
            </p>
          )}
          {messages.map((msg, i) => (
            <div
              key={i}
              className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
            >
              <div
                className={`flex max-w-[80%] items-start gap-3 rounded-xl px-4 py-3 ${
                  msg.role === 'user'
                    ? 'bg-cyan-900/60 text-cyan-50'
                    : 'bg-slate-800 text-slate-100'
                }`}
              >
                {msg.role === 'user' ? (
                  <User className="mt-1 h-4 w-4 shrink-0 opacity-60" />
                ) : (
                  <Bot className="mt-1 h-4 w-4 shrink-0 text-cyan-400" />
                )}
                <div className="prose prose-invert max-w-none prose-p:my-1">
                  <Markdown>{msg.content}</Markdown>
                </div>
              </div>
            </div>
          ))}
          {pendingConfirm && !loading && (
            <div className="flex justify-center gap-3">
              <button
                onClick={() => handleSend(true)}
                className="rounded-md bg-amber-600 px-4 py-2 text-sm font-medium hover:bg-amber-500"
              >
                Confirm &amp; proceed
              </button>
              <button
                onClick={() => setPendingConfirm(null)}
                className="rounded-md border border-slate-700 px-4 py-2 text-sm hover:bg-slate-800"
              >
                Cancel
              </button>
            </div>
          )}
          {loading && (
            <div className="flex items-center gap-2 text-sm text-slate-400">
              <RefreshCw className="h-4 w-4 animate-spin" /> thinking…
            </div>
          )}
          <div ref={endRef} />
        </section>

        <footer className="border-t border-slate-800 px-6 py-4">
          <form
            onSubmit={(e) => {
              e.preventDefault()
              handleSend()
            }}
            className="flex gap-3"
          >
            <input
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Type a message…"
              className="flex-1 rounded-md border border-slate-700 bg-slate-900 px-4 py-2 outline-none focus:border-cyan-500"
            />
            <button
              type="submit"
              disabled={loading || !input.trim()}
              className="inline-flex items-center gap-2 rounded-md bg-cyan-600 px-4 py-2 font-medium hover:bg-cyan-500 disabled:opacity-50"
            >
              <Send className="h-4 w-4" /> Send
            </button>
          </form>
        </footer>
      </main>

      <aside className="w-80 overflow-y-auto border-l border-slate-800 bg-slate-900/50 p-4">
        <h2 className="mb-3 flex items-center gap-2 text-sm font-semibold uppercase tracking-wide text-slate-400">
          <Power className="h-4 w-4" /> Smart Home
        </h2>
        {state && (
          <>
            <ul className="mb-4 space-y-2">
              {Object.entries(state.devices).map(([name, device]) => (
                <li
                  key={name}
                  className="flex items-center justify-between rounded-md border border-slate-800 px-3 py-2 text-sm"
                >
                  <span>{name}</span>
                  <span
                    className={
                      device.status === 'on' || device.status === 'open' || device.status === 'unlocked'
                        ? 'text-emerald-400'
                        : 'text-slate-400'
                    }
                  >
                    {device.status}
                    {device.brightness != null && ` · ${device.brightness}%`}
                    {device.temp != null && ` · ${device.temp}°C`}
                    {device.speed != null && ` · spd ${device.speed}`}
                  </span>
                </li>
              ))}
            </ul>

            <h3 className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-500">
              Tasks
            </h3>
            {state.tasks.length === 0 ? (
              <p className="text-sm text-slate-500">No tasks.</p>
            ) : (
              <ul className="mb-4 space-y-1 text-sm">
                {state.tasks.map((task) => (
                  <li key={task} className="flex items-center gap-2">
                    <span className="h-1.5 w-1.5 rounded-full bg-cyan-500" /> {task}
                  </li>
                ))}
              </ul>
            )}

            <h3 className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-500">
              Timers
            </h3>
            {state.timers.length === 0 ? (
              <p className="text-sm text-slate-500">No timers.</p>
            ) : (
              <ul className="space-y-1 text-sm">
                {state.timers.map((timer, i) => (
                  <li key={i} className="flex items-center gap-2">
                    <span className="h-1.5 w-1.5 rounded-full bg-amber-500" /> {timer.label}
                  </li>
                ))}
              </ul>
            )}
          </>
        )}
      </aside>
    </div>
  )
}
