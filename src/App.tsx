import { useEffect, useRef, useState } from 'react'
import Markdown from 'react-markdown'
import {
  Blinds,
  Bot,
  CheckCircle2,
  Clock,
  DoorClosed,
  Fan,
  Flame,
  Lightbulb,
  Mic,
  MicOff,
  Power,
  RefreshCw,
  Send,
  Snowflake,
  Tv,
  User,
  Wifi,
  WifiOff,
} from 'lucide-react'

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
  confirmationToken?: string
  pendingIntents?: string[]
}

type Message = {
  role: 'user' | 'assistant' | 'system'
  content: string
}

type SliderConfig = {
  intent: string
  key: 'brightness' | 'temp' | 'speed'
  min: number
  max: number
  step: number
  suffix: string
}

type DeviceControl = {
  key: string
  label: string
  icon: typeof Lightbulb
  onIntent: string
  offIntent: string
  activeWhen: (device: DeviceInfo) => boolean
  slider?: SliderConfig
}

const DEVICE_CONTROLS: DeviceControl[] = [
  {
    key: 'living_room_light',
    label: 'Living Room Light',
    icon: Lightbulb,
    onIntent: 'LIGHT_ON',
    offIntent: 'LIGHT_OFF',
    activeWhen: (d) => d.status === 'on',
    slider: { intent: 'SET_BRIGHTNESS', key: 'brightness', min: 0, max: 100, step: 5, suffix: '%' },
  },
  {
    key: 'bedroom_ac',
    label: 'Bedroom AC',
    icon: Snowflake,
    onIntent: 'AC_ON',
    offIntent: 'AC_OFF',
    activeWhen: (d) => d.status === 'on',
    slider: { intent: 'SET_TEMP', key: 'temp', min: 16, max: 30, step: 1, suffix: '°C' },
  },
  {
    key: 'kitchen_fan',
    label: 'Kitchen Fan',
    icon: Fan,
    onIntent: 'FAN_ON',
    offIntent: 'FAN_OFF',
    activeWhen: (d) => d.status === 'on',
    slider: { intent: 'FAN_SPEED', key: 'speed', min: 0, max: 5, step: 1, suffix: '' },
  },
  {
    key: 'living_room_tv',
    label: 'Living Room TV',
    icon: Tv,
    onIntent: 'TV_ON',
    offIntent: 'TV_OFF',
    activeWhen: (d) => d.status === 'on',
  },
  {
    key: 'bedroom_curtains',
    label: 'Bedroom Curtains',
    icon: Blinds,
    onIntent: 'CURTAIN_OPEN',
    offIntent: 'CURTAIN_CLOSE',
    activeWhen: (d) => d.status === 'open',
  },
  {
    key: 'bathroom_heater',
    label: 'Bathroom Heater',
    icon: Flame,
    onIntent: 'HEATER_ON',
    offIntent: 'HEATER_OFF',
    activeWhen: (d) => d.status === 'on',
    slider: { intent: 'HEATER_TEMP', key: 'temp', min: 0, max: 50, step: 1, suffix: '°C' },
  },
]

function cleanReply(text: string): string {
  return text.replace(/\[ACTION:.*?\]/g, '').trim()
}

function formatDuration(ms: number): string {
  const s = Math.max(0, Math.floor(ms / 1000))
  const m = Math.floor(s / 60)
  const h = Math.floor(m / 60)
  const sec = s % 60
  const min = m % 60
  if (h > 0) return `${h}h ${min}m`
  if (m > 0) return `${m}m ${sec}s`
  return `${sec}s`
}

function getRecognition(): { new (): any } | null {
  const w = window as any
  return w.SpeechRecognition || w.webkitSpeechRecognition || null
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

async function postConfirm(token: string, confirmed: boolean): Promise<ChatResponse> {
  const res = await fetch('/api/confirm', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ token, confirmed }),
  })
  if (!res.ok) {
    throw new Error(`Request failed with status ${res.status}`)
  }
  return res.json()
}

async function postAction(intent: string, args: string[] = []): Promise<ChatResponse> {
  const res = await fetch('/api/action', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ intent, args }),
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

function DeviceSlider({
  slider,
  value,
  onCommit,
}: {
  slider: SliderConfig
  value: number
  onCommit: (value: number) => void
}) {
  const [draft, setDraft] = useState(value)
  const lastRef = useRef(value)

  useEffect(() => {
    setDraft(value)
  }, [value])

  function commit(v: number) {
    if (v !== lastRef.current) {
      lastRef.current = v
      onCommit(v)
    }
  }

  return (
    <div className="mt-2">
      <div className="flex items-center justify-between text-xs text-slate-400">
        <span>{slider.key}</span>
        <span>
          {draft}
          {slider.suffix}
        </span>
      </div>
      <input
        type="range"
        min={slider.min}
        max={slider.max}
        step={slider.step}
        value={draft}
        onChange={(e) => setDraft(Number(e.target.value))}
        onPointerUp={() => commit(draft)}
        onKeyUp={() => commit(draft)}
        className="w-full accent-cyan-500"
      />
    </div>
  )
}

export default function App() {
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [state, setState] = useState<ApiState | null>(null)
  const [loading, setLoading] = useState(false)
  const [pendingToken, setPendingToken] = useState<string | null>(null)
  const [pendingIntents, setPendingIntents] = useState<string[]>([])
  const [wsConnected, setWsConnected] = useState(false)
  const [listening, setListening] = useState(false)
  const [now, setNow] = useState(Date.now())
  const endRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    fetchState().then(setState).catch(() => undefined)
  }, [])

  useEffect(() => {
    const interval = setInterval(() => setNow(Date.now()), 1000)
    return () => clearInterval(interval)
  }, [])

  useEffect(() => {
    let ws: WebSocket | null = null
    let closed = false

    function connect() {
      ws = new WebSocket(`ws://${location.host}/api/ws`)
      ws.onopen = () => setWsConnected(true)
      ws.onmessage = (event) => {
        const data = JSON.parse(event.data)
        if (data.type === 'state') {
          setState(data.state)
        } else if (data.type === 'timer') {
          setMessages((prev) => [...prev, { role: 'system', content: data.message }])
        }
      }
      ws.onclose = () => {
        setWsConnected(false)
        if (!closed) {
          setTimeout(connect, 3000)
        }
      }
    }

    connect()
    return () => {
      closed = true
      ws?.close()
    }
  }, [])

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, loading])

  function applyResult(result: ChatResponse) {
    const reply = cleanReply(result.reply)
    if (reply) {
      setMessages((prev) => [...prev, { role: 'assistant', content: reply }])
    }
    if (result.actions.length > 0) {
      setMessages((prev) => [
        ...prev,
        { role: 'system', content: result.actions.join(' · ') },
      ])
    }
    setState(result.state)
    if (result.needsConfirmation && result.confirmationToken) {
      setPendingToken(result.confirmationToken)
      setPendingIntents(result.pendingIntents ?? [])
    }
  }

  function pushError() {
    setMessages((prev) => [
      ...prev,
      { role: 'assistant', content: 'I hit a technical snag. Please try again.' },
    ])
  }

  async function handleSend() {
    const message = input.trim()
    if (!message || loading) return
    setLoading(true)
    setInput('')
    setPendingToken(null)
    setPendingIntents([])
    setMessages((prev) => [...prev, { role: 'user', content: message }])

    try {
      applyResult(await postChat(message))
    } catch {
      pushError()
    } finally {
      setLoading(false)
    }
  }

  async function handleConfirm(confirmed: boolean) {
    if (!pendingToken || loading) return
    setLoading(true)
    setPendingToken(null)
    setPendingIntents([])

    try {
      applyResult(await postConfirm(pendingToken, confirmed))
    } catch {
      pushError()
    } finally {
      setLoading(false)
    }
  }

  async function runAction(intent: string, args: string[] = []) {
    if (loading) return
    setLoading(true)
    try {
      applyResult(await postAction(intent, args))
    } catch {
      pushError()
    } finally {
      setLoading(false)
    }
  }

  function toggleDevice(control: DeviceControl) {
    if (!state) return
    const device = state.devices[control.key]
    runAction(control.activeWhen(device) ? control.offIntent : control.onIntent)
  }

  async function handleReset() {
    await fetch('/api/reset', { method: 'POST' })
    setMessages([])
    setPendingToken(null)
    setPendingIntents([])
    fetchState().then(setState).catch(() => undefined)
  }

  function startListening() {
    const Recognition = getRecognition()
    if (!Recognition) return
    const recognition = new Recognition()
    recognition.lang = 'en-IN'
    recognition.continuous = false
    recognition.interimResults = false
    recognition.onresult = (event: any) => {
      const transcript = event.results[0][0].transcript as string
      setInput(transcript)
      setListening(false)
    }
    recognition.onerror = () => setListening(false)
    recognition.onend = () => setListening(false)
    setListening(true)
    recognition.start()
  }

  return (
    <div className="flex h-screen bg-slate-950 text-slate-100">
      <main className="flex flex-1 flex-col">
        <header className="flex items-center gap-3 border-b border-slate-800 px-6 py-4">
          <Bot className="h-6 w-6 text-cyan-400" />
          <h1 className="text-lg font-semibold">KEERTHI</h1>
          <span className="text-xs text-slate-400">AI Voice Assistant</span>
          <span
            className={`ml-2 inline-flex items-center gap-1 text-xs ${
              wsConnected ? 'text-emerald-400' : 'text-slate-500'
            }`}
            title={wsConnected ? 'Live updates connected' : 'Live updates offline'}
          >
            {wsConnected ? <Wifi className="h-3.5 w-3.5" /> : <WifiOff className="h-3.5 w-3.5" />}
            {wsConnected ? 'live' : 'offline'}
          </span>
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
              className={`flex ${
                msg.role === 'user'
                  ? 'justify-end'
                  : msg.role === 'system'
                    ? 'justify-center'
                    : 'justify-start'
              }`}
            >
              <div
                className={`flex max-w-[80%] items-start gap-3 rounded-xl px-4 py-3 ${
                  msg.role === 'user'
                    ? 'bg-cyan-900/60 text-cyan-50'
                    : msg.role === 'system'
                      ? 'bg-emerald-950/60 text-emerald-100'
                      : 'bg-slate-800 text-slate-100'
                }`}
              >
                {msg.role === 'user' ? (
                  <User className="mt-1 h-4 w-4 shrink-0 opacity-60" />
                ) : msg.role === 'system' ? (
                  <CheckCircle2 className="mt-1 h-4 w-4 shrink-0 text-emerald-400" />
                ) : (
                  <Bot className="mt-1 h-4 w-4 shrink-0 text-cyan-400" />
                )}
                <div className="prose prose-invert max-w-none prose-p:my-1">
                  <Markdown>{msg.content}</Markdown>
                </div>
              </div>
            </div>
          ))}
          {pendingToken && !loading && (
            <div className="flex flex-col items-center gap-2">
              <p className="text-sm text-slate-400">
                Confirm this safety-sensitive action:{' '}
                <span className="font-medium text-amber-300">
                  {pendingIntents.join(', ') || 'proceed'}
                </span>
              </p>
              <div className="flex gap-3">
                <button
                  onClick={() => handleConfirm(true)}
                  className="rounded-md bg-amber-600 px-4 py-2 text-sm font-medium hover:bg-amber-500"
                >
                  Confirm &amp; proceed
                </button>
                <button
                  onClick={() => handleConfirm(false)}
                  className="rounded-md border border-slate-700 px-4 py-2 text-sm hover:bg-slate-800"
                >
                  Cancel
                </button>
              </div>
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
            <button
              type="button"
              onClick={startListening}
              disabled={loading || !getRecognition()}
              className="inline-flex items-center gap-2 rounded-md border border-slate-700 px-4 py-2 text-sm hover:bg-slate-800 disabled:opacity-40"
              title="Voice input"
            >
              {listening ? <MicOff className="h-4 w-4 text-red-400" /> : <Mic className="h-4 w-4" />}
              <span className="hidden sm:inline">{listening ? 'Listening…' : 'Mic'}</span>
            </button>
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
              {DEVICE_CONTROLS.map((control) => {
                const device = state.devices[control.key]
                if (!device) return null
                const active = control.activeWhen(device)
                const Icon = control.icon
                return (
                  <li
                    key={control.key}
                    className="rounded-md border border-slate-800 px-3 py-2 text-sm"
                  >
                    <div className="flex items-center justify-between">
                      <span className="flex items-center gap-2">
                        <Icon
                          className={`h-4 w-4 ${active ? 'text-cyan-400' : 'text-slate-500'}`}
                        />
                        {control.label}
                      </span>
                      <button
                        onClick={() => toggleDevice(control)}
                        className={`rounded-md px-2 py-1 text-xs font-medium ${
                          active
                            ? 'bg-emerald-600/20 text-emerald-300 hover:bg-emerald-600/30'
                            : 'bg-slate-800 text-slate-400 hover:bg-slate-700'
                        }`}
                      >
                        {active ? 'ON' : 'OFF'}
                      </button>
                    </div>
                    {control.slider && (
                      <DeviceSlider
                        slider={control.slider}
                        value={Number(device[control.slider.key] ?? 0)}
                        onCommit={(v) =>
                          runAction(control.slider!.intent, [String(v)])
                        }
                      />
                    )}
                  </li>
                )
              })}
              <li className="flex items-center justify-between rounded-md border border-slate-800 px-3 py-2 text-sm">
                <span className="flex items-center gap-2">
                  <DoorClosed className="h-4 w-4 text-slate-500" />
                  Main Door
                </span>
                <span
                  className={
                    state.devices.main_door?.status === 'unlocked'
                      ? 'text-amber-400'
                      : 'text-emerald-400'
                  }
                >
                  {state.devices.main_door?.status}
                </span>
              </li>
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

            <h3 className="mb-2 flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-slate-500">
              <Clock className="h-3.5 w-3.5" /> Timers
            </h3>
            {state.timers.length === 0 ? (
              <p className="text-sm text-slate-500">No timers.</p>
            ) : (
              <ul className="space-y-1 text-sm">
                {state.timers.map((timer, i) => (
                  <li key={i} className="flex items-center justify-between gap-2">
                    <span className="flex items-center gap-2">
                      <span className="h-1.5 w-1.5 rounded-full bg-amber-500" /> {timer.label}
                    </span>
                    <span className="font-mono text-xs text-amber-300">
                      {formatDuration(timer.due * 1000 - now)}
                    </span>
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
