import { useEffect, useRef, useState } from 'react'
import Markdown from 'react-markdown'
import {
  AppWindow,
  Bot,
  Camera,
  CheckCircle2,
  Clock,
  Cpu,
  Database,
  FolderOpen,
  HardDrive,
  LayoutGrid,
  Lock,
  Maximize,
  Mic,
  MicOff,
  Minimize,
  Monitor,
  Moon,
  Play,
  Power,
  RefreshCw,
  Send,
  Sun,
  Terminal,
  Trash2,
  User,
  Volume2,
  VolumeX,
  Wifi,
  WifiOff,
  X,
} from 'lucide-react'

type SystemMetrics = {
  cpu: number
  cores: number
  memoryUsed: number
  memoryTotal: number
  memoryPercent: number
  diskUsed: number
  diskTotal: number
  diskPercent: number
  batteryPercent: number | null
  batteryCharging: boolean | null
  uptime: number
  platform: string
  hostname: string
  python: string
}

type ProcessInfo = {
  pid: number
  name: string
  cpu: number
  memory: number
}

type WindowInfo = {
  hwnd: number
  title: string
}

type ApiState = {
  system: SystemMetrics
  processes: ProcessInfo[]
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

const KNOWN_APPS = [
  'notepad',
  'calculator',
  'paint',
  'explorer',
  'task manager',
  'command prompt',
  'powershell',
  'control panel',
  'snipping tool',
  'chrome',
  'edge',
  'firefox',
  'settings',
  'terminal',
  'word',
  'excel',
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

function formatBytes(n: number): string {
  const units = ['B', 'KB', 'MB', 'GB', 'TB']
  let size = n
  let i = 0
  while (size >= 1024 && i < units.length - 1) {
    size /= 1024
    i++
  }
  return `${size.toFixed(i === 0 ? 0 : 1)} ${units[i]}`
}

function formatUptime(seconds: number): string {
  const d = Math.floor(seconds / 86400)
  const h = Math.floor((seconds % 86400) / 3600)
  const m = Math.floor((seconds % 3600) / 60)
  if (d > 0) return `${d}d ${h}h`
  if (h > 0) return `${h}h ${m}m`
  return `${m}m`
}

async function toPcm16(blob: Blob): Promise<ArrayBuffer> {
  const arrayBuffer = await blob.arrayBuffer()
  const audioCtx = new AudioContext()
  try {
    const decoded = await audioCtx.decodeAudioData(arrayBuffer)
    const targetRate = 16000
    const offline = new OfflineAudioContext(
      1,
      Math.ceil(decoded.duration * targetRate),
      targetRate,
    )
    const source = offline.createBufferSource()
    source.buffer = decoded
    source.connect(offline.destination)
    source.start()
    const rendered = await offline.startRendering()
    const channel = rendered.getChannelData(0)
    const pcm = new Int16Array(channel.length)
    for (let i = 0; i < channel.length; i++) {
      pcm[i] = Math.max(-1, Math.min(1, channel[i])) * 0x7fff
    }
    return pcm.buffer
  } finally {
    audioCtx.close()
  }
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

function Gauge({
  label,
  value,
  color,
}: {
  label: string
  value: number | null
  color: string
}) {
  const pct = value === null ? 0 : Math.max(0, Math.min(100, value))
  const r = 26
  const c = 2 * Math.PI * r
  const dash = (pct / 100) * c
  return (
    <div className="flex flex-col items-center gap-1">
      <svg width="68" height="68" viewBox="0 0 64 64">
        <circle cx="32" cy="32" r={r} fill="none" strokeWidth="6" className="stroke-slate-800" />
        <circle
          cx="32"
          cy="32"
          r={r}
          fill="none"
          strokeWidth="6"
          stroke={color}
          strokeLinecap="round"
          strokeDasharray={`${dash} ${c}`}
          transform="rotate(-90 32 32)"
        />
        <text
          x="32"
          y="35"
          textAnchor="middle"
          fill="currentColor"
          fontSize="13"
          fontWeight="600"
          className="fill-slate-100"
        >
          {value === null ? '—' : value}
        </text>
      </svg>
      <span className="text-[11px] text-slate-400">{label}</span>
    </div>
  )
}

function FileBrowser() {
  const [path, setPath] = useState('')
  const [listing, setListing] = useState<{ path: string; entries: { name: string; isDir: boolean }[] } | null>(null)
  const [error, setError] = useState<string | null>(null)

  async function load(target: string) {
    try {
      const params = new URLSearchParams()
      if (target) params.set('path', target)
      const res = await fetch(`/api/files?${params}`)
      if (!res.ok) throw new Error(String(res.status))
      const data = await res.json()
      setListing(data)
      setPath(data.path ?? target)
      setError(data.error ?? null)
    } catch {
      setError('Could not read that folder.')
    }
  }

  useEffect(() => {
    load('')
  }, [])

  const parts = (listing?.path ?? '').split(/[\\/]/)

  return (
    <div>
      <div className="mb-2 flex gap-2">
        <input
          value={path}
          onChange={(e) => setPath(e.target.value)}
          placeholder="Folder path (e.g. C:\Users)"
          className="min-w-0 flex-1 rounded-md border border-slate-700 bg-slate-900 px-2 py-1 text-xs outline-none focus:border-cyan-500"
        />
        <button
          onClick={() => load(path)}
          className="rounded-md bg-slate-800 px-2 py-1 text-xs hover:bg-slate-700"
        >
          Go
        </button>
      </div>
      {error && <p className="mb-2 text-xs text-red-400">{error}</p>}
      <div className="max-h-40 overflow-y-auto rounded-md border border-slate-800">
        <button
          onClick={() => load(parts.slice(0, -1).join('\\') || '\\')}
          className="block w-full px-2 py-1 text-left text-xs text-slate-400 hover:bg-slate-800"
        >
          ← up one level
        </button>
        {(listing?.entries ?? []).map((entry) => (
          <div
            key={entry.name}
            className="flex items-center justify-between px-2 py-1 text-xs hover:bg-slate-800"
          >
            <button
              onClick={() => (entry.isDir ? load(joinPath(path, entry.name)) : undefined)}
              className="flex min-w-0 items-center gap-1.5 truncate text-left"
            >
              <FolderOpen className={`h-3.5 w-3.5 shrink-0 ${entry.isDir ? 'text-amber-400' : 'text-slate-500'}`} />
              <span className="truncate">{entry.name}</span>
            </button>
            {!entry.isDir && (
              <button
                onClick={() => postAction('OPEN_FILE', [joinPath(path, entry.name)])}
                className="shrink-0 text-cyan-400 hover:text-cyan-300"
                title="Open file"
              >
                <Play className="h-3.5 w-3.5" />
              </button>
            )}
          </div>
        ))}
      </div>
    </div>
  )
}

function joinPath(dir: string, name: string): string {
  return dir ? `${dir.replace(/[\\/]+$/, '')}\\${name}` : name
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
  const [selectedApp, setSelectedApp] = useState(KNOWN_APPS[0])
  const [command, setCommand] = useState('')
  const [urlInput, setUrlInput] = useState('')
  const [now, setNow] = useState(Date.now())
  const [volume, setVolume] = useState(50)
  const [muted, setMuted] = useState(false)
  const [brightness, setBrightness] = useState(80)
  const [screenshot, setScreenshot] = useState<string | null>(null)
  const [windows, setWindows] = useState<WindowInfo[]>([])
  const recorderRef = useRef<MediaRecorder | null>(null)
  const endRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    fetchState().then(setState).catch(() => undefined)
    const interval = setInterval(() => {
      fetchState().then(setState).catch(() => undefined)
    }, 2000)
    return () => clearInterval(interval)
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

  async function sendMessage(message: string) {
    const text = message.trim()
    if (!text || loading) return
    setLoading(true)
    setInput('')
    setPendingToken(null)
    setPendingIntents([])
    setMessages((prev) => [...prev, { role: 'user', content: text }])

    try {
      applyResult(await postChat(text))
    } catch {
      pushError()
    } finally {
      setLoading(false)
    }
  }

  async function handleSend() {
    sendMessage(input)
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

  async function takeScreenshot() {
    if (loading) return
    setLoading(true)
    try {
      await postAction('TAKE_SCREENSHOT', [])
      setScreenshot(`/api/screenshot?t=${Date.now()}`)
    } catch {
      pushError()
    } finally {
      setLoading(false)
    }
  }

  async function loadWindows() {
    try {
      const res = await fetch('/api/windows')
      if (!res.ok) throw new Error(String(res.status))
      const data = await res.json()
      setWindows(data.windows ?? [])
    } catch {
      setWindows([])
    }
  }

  useEffect(() => {
    loadWindows()
  }, [])

  async function handleReset() {
    await fetch('/api/reset', { method: 'POST' })
    setMessages([])
    setPendingToken(null)
    setPendingIntents([])
    fetchState().then(setState).catch(() => undefined)
  }

  function startListening() {
    if (listening) {
      recorderRef.current?.stop()
      return
    }
    navigator.mediaDevices
      .getUserMedia({ audio: true })
      .then((stream) => {
        setListening(true)
        const recorder = new MediaRecorder(stream)
        recorderRef.current = recorder
        const chunks: Blob[] = []
        recorder.ondataavailable = (e) => {
          if (e.data.size > 0) chunks.push(e.data)
        }
        recorder.onstop = async () => {
          stream.getTracks().forEach((track) => track.stop())
          setListening(false)
          try {
            const blob = new Blob(chunks, { type: recorder.mimeType })
            const pcm = await toPcm16(blob)
            const res = await fetch('/api/transcribe', {
              method: 'POST',
              headers: { 'Content-Type': 'application/octet-stream' },
              body: pcm,
            })
            if (!res.ok) throw new Error(String(res.status))
            const data = await res.json()
            sendMessage(data.text)
          } catch {
            pushError()
          }
        }
        recorder.start()
      })
      .catch(() => {
        setListening(false)
        setMessages((prev) => [
          ...prev,
          {
            role: 'assistant',
            content:
              "I couldn't access your microphone — allow mic permission in the browser and try again.",
          },
        ])
      })
  }

  const system = state?.system

  return (
    <div className="flex h-screen bg-slate-950 text-slate-100">
      <main className="flex flex-1 flex-col">
        <header className="flex items-center gap-3 border-b border-slate-800 px-6 py-4">
          <Bot className="h-6 w-6 text-cyan-400" />
          <h1 className="text-lg font-semibold">KEERTHI</h1>
          <span className="text-xs text-slate-400">System Assistant</span>
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
              Ask KEERTHI to check CPU usage, open an app, run a command, or set a timer.
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
              disabled={loading}
              className="inline-flex items-center gap-2 rounded-md border border-slate-700 px-4 py-2 text-sm hover:bg-slate-800 disabled:opacity-40"
              title="Voice input"
            >
              {listening ? <MicOff className="h-4 w-4 text-red-400" /> : <Mic className="h-4 w-4" />}
              <span className="hidden sm:inline">{listening ? 'Recording… tap to stop' : 'Mic'}</span>
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

      <aside className="w-[22rem] overflow-y-auto border-l border-slate-800 bg-slate-900/50 p-4">
        {system && (
          <>
            <h2 className="mb-3 flex items-center gap-2 text-sm font-semibold uppercase tracking-wide text-slate-400">
              <Monitor className="h-4 w-4" /> {system.hostname}
            </h2>
            <div className="mb-2 grid grid-cols-4 gap-2">
              <Gauge label="CPU" value={system.cpu} color="#22d3ee" />
              <Gauge label="RAM" value={system.memoryPercent} color="#a78bfa" />
              <Gauge label="Disk" value={system.diskPercent} color="#34d399" />
              <Gauge
                label="Battery"
                value={system.batteryPercent}
                color="#fbbf24"
              />
            </div>
            <div className="mb-4 grid grid-cols-2 gap-x-3 gap-y-1 rounded-md border border-slate-800 px-3 py-2 text-xs text-slate-400">
              <span>
                <Cpu className="mr-1 inline h-3.5 w-3.5" />
                {system.cores} cores
              </span>
              <span>
                <Clock className="mr-1 inline h-3.5 w-3.5" />
                up {formatUptime(system.uptime)}
              </span>
              <span className="col-span-2">
                <HardDrive className="mr-1 inline h-3.5 w-3.5" />
                {formatBytes(system.memoryUsed)} / {formatBytes(system.memoryTotal)} RAM ·{' '}
                {formatBytes(system.diskUsed)} / {formatBytes(system.diskTotal)} disk
              </span>
              <span className="col-span-2 text-slate-500">
                {system.platform} · Python {system.python}
              </span>
            </div>

            <h3 className="mb-2 flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-slate-500">
              <Play className="h-3.5 w-3.5" /> Launch App
            </h3>
            <div className="mb-4 flex gap-2">
              <select
                value={selectedApp}
                onChange={(e) => setSelectedApp(e.target.value)}
                className="min-w-0 flex-1 rounded-md border border-slate-700 bg-slate-900 px-2 py-1.5 text-sm outline-none focus:border-cyan-500"
              >
                {KNOWN_APPS.map((app) => (
                  <option key={app} value={app}>
                    {app}
                  </option>
                ))}
              </select>
              <button
                onClick={() => runAction('OPEN_APP', [selectedApp])}
                disabled={loading}
                aria-label="Open selected app"
                className="rounded-md bg-cyan-600 px-3 py-1.5 text-sm font-medium hover:bg-cyan-500 disabled:opacity-50"
              >
                Open
              </button>
            </div>

            <h3 className="mb-2 flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-slate-500">
              <Volume2 className="h-3.5 w-3.5" /> Power &amp; Media
            </h3>
            <div className="mb-4 space-y-2.5 rounded-md border border-slate-800 p-3">
              <div className="flex items-center gap-2">
                <Volume2 className="h-4 w-4 shrink-0 text-slate-400" />
                <input
                  type="range"
                  min={0}
                  max={100}
                  value={volume}
                  onChange={(e) => setVolume(Number(e.target.value))}
                  onPointerUp={() => runAction('SET_VOLUME', [String(volume)])}
                  className="flex-1 accent-cyan-500"
                  aria-label="Volume"
                />
                <button
                  onClick={() => {
                    setMuted(!muted)
                    runAction('MUTE', [muted ? 'off' : 'on'])
                  }}
                  disabled={loading}
                  className="text-slate-400 hover:text-slate-200 disabled:opacity-40"
                  title={muted ? 'Unmute' : 'Mute'}
                >
                  {muted ? <VolumeX className="h-4 w-4" /> : <Volume2 className="h-4 w-4" />}
                </button>
              </div>
              <div className="flex items-center gap-2">
                <Sun className="h-4 w-4 shrink-0 text-slate-400" />
                <input
                  type="range"
                  min={0}
                  max={100}
                  value={brightness}
                  onChange={(e) => setBrightness(Number(e.target.value))}
                  onPointerUp={() => runAction('SET_BRIGHTNESS', [String(brightness)])}
                  className="flex-1 accent-cyan-500"
                  aria-label="Brightness"
                />
              </div>
              <div className="flex gap-1.5 pt-0.5">
                <button
                  onClick={() => runAction('LOCK_SCREEN')}
                  disabled={loading}
                  className="flex-1 rounded-md bg-slate-800 px-2 py-1.5 text-xs hover:bg-slate-700 disabled:opacity-40"
                  title="Lock screen"
                >
                  <Lock className="mx-auto h-4 w-4" />
                </button>
                <button
                  onClick={() => runAction('SLEEP')}
                  disabled={loading}
                  className="flex-1 rounded-md bg-slate-800 px-2 py-1.5 text-xs hover:bg-slate-700 disabled:opacity-40"
                  title="Sleep"
                >
                  <Moon className="mx-auto h-4 w-4" />
                </button>
                <button
                  onClick={() => runAction('RESTART')}
                  disabled={loading}
                  className="flex-1 rounded-md bg-slate-800 px-2 py-1.5 text-xs hover:bg-slate-700 disabled:opacity-40"
                  title="Restart"
                >
                  <RefreshCw className="mx-auto h-4 w-4" />
                </button>
                <button
                  onClick={() => runAction('SHUTDOWN')}
                  disabled={loading}
                  className="flex-1 rounded-md bg-red-950/60 px-2 py-1.5 text-xs hover:bg-red-900/60 disabled:opacity-40"
                  title="Shut down"
                >
                  <Power className="mx-auto h-4 w-4" />
                </button>
              </div>
            </div>

            <h3 className="mb-2 flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-slate-500">
              <Terminal className="h-3.5 w-3.5" /> Run Command
            </h3>
            <div className="mb-4 flex gap-2">
              <input
                value={command}
                onChange={(e) => setCommand(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' && command.trim()) {
                    runAction('RUN_COMMAND', [command])
                    setCommand('')
                  }
                }}
                placeholder="e.g. echo hello"
                className="min-w-0 flex-1 rounded-md border border-slate-700 bg-slate-900 px-2 py-1.5 text-sm outline-none focus:border-cyan-500"
              />
              <button
                onClick={() => {
                  if (command.trim()) {
                    runAction('RUN_COMMAND', [command])
                    setCommand('')
                  }
                }}
                disabled={loading || !command.trim()}
                className="rounded-md bg-slate-800 px-3 py-1.5 text-sm hover:bg-slate-700 disabled:opacity-50"
              >
                Run
              </button>
            </div>

            <h3 className="mb-2 flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-slate-500">
              <Wifi className="h-3.5 w-3.5" /> Browser
            </h3>
            <div className="mb-4 flex gap-2">
              <input
                value={urlInput}
                onChange={(e) => setUrlInput(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' && urlInput.trim()) {
                    runAction('OPEN_URL', [urlInput])
                    setUrlInput('')
                  }
                }}
                placeholder="URL or search…"
                className="min-w-0 flex-1 rounded-md border border-slate-700 bg-slate-900 px-2 py-1.5 text-sm outline-none focus:border-cyan-500"
              />
              <button
                onClick={() => {
                  if (urlInput.trim()) {
                    runAction('OPEN_URL', [urlInput])
                    setUrlInput('')
                  }
                }}
                disabled={loading || !urlInput.trim()}
                aria-label="Open URL"
                className="rounded-md bg-cyan-600 px-2.5 py-1.5 text-sm font-medium hover:bg-cyan-500 disabled:opacity-50"
                title="Open URL"
              >
                Open
              </button>
              <button
                onClick={() => {
                  if (urlInput.trim()) {
                    runAction('WEB_SEARCH', [urlInput])
                    setUrlInput('')
                  }
                }}
                disabled={loading || !urlInput.trim()}
                aria-label="Web search"
                className="rounded-md bg-slate-800 px-2.5 py-1.5 text-sm hover:bg-slate-700 disabled:opacity-50"
                title="Web search"
              >
                Search
              </button>
            </div>

            <h3 className="mb-2 flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-slate-500">
              <FolderOpen className="h-3.5 w-3.5" /> Files
            </h3>
            <div className="mb-4">
              <FileBrowser />
            </div>

            <h3 className="mb-2 flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-slate-500">
              <Camera className="h-3.5 w-3.5" /> Screenshot
            </h3>
            <div className="mb-4">
              <button
                onClick={takeScreenshot}
                disabled={loading}
                className="w-full rounded-md bg-slate-800 px-3 py-1.5 text-sm hover:bg-slate-700 disabled:opacity-50"
              >
                Capture screen
              </button>
              {screenshot && (
                <img
                  src={screenshot}
                  alt="Screen capture"
                  className="mt-2 w-full rounded-md border border-slate-800"
                />
              )}
            </div>

            <h3 className="mb-2 flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-slate-500">
              <Database className="h-3.5 w-3.5" /> Processes
            </h3>
            <div className="mb-4 max-h-48 overflow-y-auto rounded-md border border-slate-800">
              <table className="w-full text-xs">
                <thead className="sticky top-0 bg-slate-900 text-slate-500">
                  <tr>
                    <th className="px-2 py-1 text-left font-medium">Name</th>
                    <th className="px-2 py-1 text-right font-medium">CPU</th>
                    <th className="px-2 py-1 text-right font-medium">MEM</th>
                    <th className="px-2 py-1" />
                  </tr>
                </thead>
                <tbody>
                  {(state?.processes ?? []).map((proc) => (
                    <tr key={proc.pid} className="border-t border-slate-800/60">
                      <td className="max-w-[8rem] truncate px-2 py-1" title={`PID ${proc.pid}`}>
                        {proc.name}
                      </td>
                      <td className="px-2 py-1 text-right">{proc.cpu}%</td>
                      <td className="px-2 py-1 text-right">{proc.memory}%</td>
                      <td className="px-2 py-1 text-right">
                        <button
                          onClick={() => runAction('KILL_PROCESS', [String(proc.pid)])}
                          disabled={loading}
                          className="text-red-400 hover:text-red-300 disabled:opacity-40"
                          title={`Kill ${proc.name} (PID ${proc.pid})`}
                        >
                          <Trash2 className="h-3.5 w-3.5" />
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            <h3 className="mb-2 flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-slate-500">
              <AppWindow className="h-3.5 w-3.5" /> Windows
            </h3>
            <div className="mb-4">
              <button
                onClick={loadWindows}
                className="mb-2 w-full rounded-md bg-slate-800 px-3 py-1.5 text-sm hover:bg-slate-700"
              >
                Refresh windows
              </button>
              {windows.length === 0 ? (
                <p className="text-sm text-slate-500">No open windows.</p>
              ) : (
                <ul className="max-h-40 space-y-1 overflow-y-auto rounded-md border border-slate-800 p-2">
                  {windows.map((w) => (
                    <li
                      key={w.hwnd}
                      className="flex items-center gap-1.5 text-xs"
                    >
                      <span className="min-w-0 flex-1 truncate text-slate-300" title={w.title}>
                        {w.title}
                      </span>
                      <button
                        onClick={() => runAction('FOCUS_WINDOW', [w.title])}
                        disabled={loading}
                        className="text-slate-400 hover:text-cyan-300 disabled:opacity-40"
                        title="Focus"
                      >
                        <LayoutGrid className="h-3.5 w-3.5" />
                      </button>
                      <button
                        onClick={() => runAction('MINIMIZE_WINDOW', [w.title])}
                        disabled={loading}
                        className="text-slate-400 hover:text-amber-300 disabled:opacity-40"
                        title="Minimize"
                      >
                        <Minimize className="h-3.5 w-3.5" />
                      </button>
                      <button
                        onClick={() => runAction('MAXIMIZE_WINDOW', [w.title])}
                        disabled={loading}
                        className="text-slate-400 hover:text-emerald-300 disabled:opacity-40"
                        title="Maximize"
                      >
                        <Maximize className="h-3.5 w-3.5" />
                      </button>
                      <button
                        onClick={() => runAction('CLOSE_WINDOW', [w.title])}
                        disabled={loading}
                        className="text-slate-400 hover:text-red-300 disabled:opacity-40"
                        title="Close"
                      >
                        <X className="h-3.5 w-3.5" />
                      </button>
                    </li>
                  ))}
                </ul>
              )}
            </div>

            <h3 className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-500">
              Tasks
            </h3>
            {state?.tasks.length === 0 ? (
              <p className="mb-4 text-sm text-slate-500">No tasks.</p>
            ) : (
              <ul className="mb-4 space-y-1 text-sm">
                {state?.tasks.map((task) => (
                  <li key={task} className="flex items-center gap-2">
                    <span className="h-1.5 w-1.5 rounded-full bg-cyan-500" /> {task}
                  </li>
                ))}
              </ul>
            )}

            <h3 className="mb-2 flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-slate-500">
              <Clock className="h-3.5 w-3.5" /> Timers
            </h3>
            {state?.timers.length === 0 ? (
              <p className="text-sm text-slate-500">No timers.</p>
            ) : (
              <ul className="space-y-1 text-sm">
                {state?.timers.map((timer, i) => (
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
