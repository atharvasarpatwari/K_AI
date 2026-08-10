import { useEffect, useRef, useState } from 'react'
import type { ButtonHTMLAttributes, CSSProperties, ReactNode } from 'react'
import Markdown from 'react-markdown'
import type { LucideIcon } from 'lucide-react'
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
  PanelLeftClose,
  PanelLeftOpen,
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

const SUGGESTIONS = [
  'What is my CPU usage?',
  'Open Notepad',
  'Set a timer for 5 minutes',
  'Show me my open windows',
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

type ButtonProps = ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: 'primary' | 'ghost' | 'soft' | 'danger'
  loading?: boolean
}

function Button({
  variant = 'soft',
  loading = false,
  className = '',
  children,
  disabled,
  ...rest
}: ButtonProps) {
  const variantClass = {
    primary: 'btn-primary',
    ghost: 'btn-ghost',
    soft: 'btn-soft',
    danger: 'btn-danger',
  }[variant]
  return (
    <button className={`btn ${variantClass} ${className}`} disabled={disabled || loading} {...rest}>
      {loading && <RefreshCw className="h-3.5 w-3.5 animate-spin" />}
      {children}
    </button>
  )
}

function Card({ className = '', children }: { className?: string; children: ReactNode }) {
  return <div className={`card ${className}`}>{children}</div>
}

const SECTION_TONES = {
  cyan: 'bg-cyan-500/10 text-cyan-300 ring-cyan-400/30',
  amber: 'bg-amber-500/10 text-amber-300 ring-amber-400/30',
  emerald: 'bg-emerald-500/10 text-emerald-300 ring-emerald-400/30',
  violet: 'bg-violet-500/10 text-violet-300 ring-violet-400/30',
  red: 'bg-red-500/10 text-red-300 ring-red-400/30',
} as const

function SectionHeader({
  icon: Icon,
  title,
  tone = 'cyan',
}: {
  icon: LucideIcon
  title: string
  tone?: keyof typeof SECTION_TONES
}) {
  return (
    <div className="mb-2.5 flex items-center gap-2">
      <span className={`flex h-6 w-6 items-center justify-center rounded-lg ring-1 ${SECTION_TONES[tone]}`}>
        <Icon className="h-3.5 w-3.5" />
      </span>
      <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-400">{title}</h3>
    </div>
  )
}

function Slider({
  icon: Icon,
  value,
  onChange,
  onCommit,
  ariaLabel,
  showValue = false,
  children,
}: {
  icon: LucideIcon
  value: number
  onChange: (v: number) => void
  onCommit: () => void
  ariaLabel: string
  showValue?: boolean
  children?: ReactNode
}) {
  return (
    <div className="flex items-center gap-2.5">
      <Icon className="h-4 w-4 shrink-0 text-slate-400" />
      <input
        type="range"
        min={0}
        max={100}
        value={value}
        onChange={(e) => onChange(Number(e.target.value))}
        onPointerUp={onCommit}
        onKeyUp={(e) => {
          if (['ArrowUp', 'ArrowDown', 'ArrowLeft', 'ArrowRight', 'Home', 'End'].includes(e.key)) {
            onCommit()
          }
        }}
        aria-label={ariaLabel}
        className="slider flex-1"
        style={{ '--fill': `${value}%` } as CSSProperties}
      />
      {showValue && (
        <span className="w-9 shrink-0 text-right font-mono text-xs text-slate-400">{value}%</span>
      )}
      {children}
    </div>
  )
}

function Gauge({ label, value, color }: { label: string; value: number | null; color: string }) {
  const pct = value === null ? 0 : Math.max(0, Math.min(100, value))
  const r = 26
  const c = 2 * Math.PI * r
  const dash = (pct / 100) * c
  const gid = `gauge-${color.slice(1)}`
  return (
    <div className="flex flex-col items-center gap-1.5">
      <div className="relative" style={{ filter: `drop-shadow(0 0 7px ${color}55)` }}>
        <svg width="72" height="72" viewBox="0 0 64 64" className="block">
          <defs>
            <linearGradient id={gid} x1="0%" y1="0%" x2="100%" y2="100%">
              <stop offset="0%" stopColor={color} />
              <stop offset="100%" stopColor="#ffffff" stopOpacity="0.55" />
            </linearGradient>
          </defs>
          <circle cx="32" cy="32" r={r} fill="none" strokeWidth="6" className="stroke-slate-800/80" />
          <circle
            cx="32"
            cy="32"
            r={r}
            fill="none"
            strokeWidth="6"
            stroke={`url(#${gid})`}
            strokeLinecap="round"
            strokeDasharray={`${dash} ${c}`}
            transform="rotate(-90 32 32)"
            className="transition-all duration-700 ease-out"
          />
        </svg>
        <span className="absolute inset-0 flex items-center justify-center text-sm font-bold text-slate-100">
          {value === null ? '—' : value}
        </span>
      </div>
      <span className="text-[11px] font-medium uppercase tracking-wide text-slate-400">{label}</span>
    </div>
  )
}

function TypingIndicator() {
  return (
    <div className="animate-fade-in flex items-center gap-2.5 text-sm text-slate-400">
      <span className="flex gap-1">
        <span className="typing-dot h-1.5 w-1.5 rounded-full bg-cyan-400" />
        <span className="typing-dot h-1.5 w-1.5 rounded-full bg-cyan-400" style={{ animationDelay: '0.15s' }} />
        <span className="typing-dot h-1.5 w-1.5 rounded-full bg-cyan-400" style={{ animationDelay: '0.3s' }} />
      </span>
      <span>thinking…</span>
    </div>
  )
}

function ChatBubble({ msg }: { msg: Message }) {
  const isUser = msg.role === 'user'
  const isSystem = msg.role === 'system'
  return (
    <div
      className={`animate-fade-up flex ${isUser ? 'justify-end' : isSystem ? 'justify-center' : 'justify-start'}`}
    >
      <div
        className={`flex max-w-[85%] items-start gap-2.5 px-4 py-3 sm:max-w-[75%] ${
          isUser
            ? 'rounded-2xl rounded-br-md bg-gradient-to-br from-cyan-500/90 to-cyan-800/90 text-cyan-50 shadow-lg shadow-cyan-950/40 ring-1 ring-cyan-300/20'
            : isSystem
              ? 'rounded-xl border border-emerald-500/20 bg-emerald-950/40 text-emerald-100'
              : 'rounded-2xl rounded-bl-md border border-slate-700/60 bg-slate-900/70 text-slate-100 shadow-lg shadow-black/20'
        }`}
      >
        {isUser ? (
          <span className="mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-lg bg-cyan-950/40 ring-1 ring-cyan-300/30">
            <User className="h-3.5 w-3.5 text-cyan-200" />
          </span>
        ) : isSystem ? (
          <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0 text-emerald-400" />
        ) : (
          <span className="mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-lg bg-gradient-to-br from-cyan-300 to-cyan-600">
            <Bot className="h-3.5 w-3.5 text-slate-950" />
          </span>
        )}
        <div className="prose prose-invert max-w-none prose-p:my-1 prose-ul:my-1">
          <Markdown>{msg.content}</Markdown>
        </div>
      </div>
    </div>
  )
}

function EmptyState({ onSuggest }: { onSuggest: (text: string) => void }) {
  return (
    <div className="flex flex-col items-center px-4 pt-16 text-center sm:pt-24">
      <div className="mb-5 flex h-16 w-16 items-center justify-center rounded-3xl bg-gradient-to-br from-cyan-400 to-cyan-700 shadow-lg shadow-cyan-900/50 ring-1 ring-cyan-300/30">
        <Bot className="h-8 w-8 text-slate-950" />
      </div>
      <h2 className="mb-1.5 text-lg font-semibold text-slate-200">How can I help?</h2>
      <p className="max-w-md text-sm leading-relaxed text-slate-500">
        Ask KEERTHI to check CPU usage, open an app, run a command, or set a timer.
      </p>
      <div className="mt-6 flex max-w-md flex-wrap items-center justify-center gap-2">
        {SUGGESTIONS.map((s) => (
          <button key={s} type="button" onClick={() => onSuggest(s)} className="chip">
            {s}
          </button>
        ))}
      </div>
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
          className="input min-w-0 flex-1 py-1.5 text-xs"
        />
        <Button variant="soft" onClick={() => load(path)} className="px-3 text-xs">
          Go
        </Button>
      </div>
      {error && <p className="mb-2 text-xs text-red-400">{error}</p>}
      <div className="max-h-40 overflow-y-auto rounded-xl border border-slate-800/80">
        <button
          type="button"
          onClick={() => load(parts.slice(0, -1).join('\\') || '\\')}
          className="block w-full px-2 py-1.5 text-left text-xs text-slate-400 transition-colors hover:bg-slate-800/70 hover:text-cyan-300"
        >
          ← up one level
        </button>
        {(listing?.entries ?? []).map((entry) => (
          <div
            key={entry.name}
            className="group flex items-center justify-between px-2 py-1.5 text-xs transition-colors hover:bg-slate-800/50"
          >
            <button
              type="button"
              onClick={() => (entry.isDir ? load(joinPath(path, entry.name)) : undefined)}
              className="flex min-w-0 items-center gap-1.5 truncate text-left"
            >
              <FolderOpen className={`h-3.5 w-3.5 shrink-0 ${entry.isDir ? 'text-amber-400' : 'text-slate-500'}`} />
              <span className="truncate text-slate-300">{entry.name}</span>
            </button>
            {!entry.isDir && (
              <button
                type="button"
                onClick={() => postAction('OPEN_FILE', [joinPath(path, entry.name)])}
                className="shrink-0 text-cyan-400 opacity-0 transition-opacity hover:text-cyan-300 group-hover:opacity-100"
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
  const [sidebarOpen, setSidebarOpen] = useState(
    () => typeof window === 'undefined' || window.innerWidth >= 1024,
  )
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

  function handleSend() {
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

  function handleReset() {
    fetch('/api/reset', { method: 'POST' })
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

  function runCommandNow() {
    if (command.trim()) {
      runAction('RUN_COMMAND', [command])
      setCommand('')
    }
  }

  function openUrl() {
    if (urlInput.trim()) {
      runAction('OPEN_URL', [urlInput])
      setUrlInput('')
    }
  }

  function searchWeb() {
    if (urlInput.trim()) {
      runAction('WEB_SEARCH', [urlInput])
      setUrlInput('')
    }
  }

  const system = state?.system

  return (
    <div className="flex h-screen overflow-hidden text-slate-100">
      <main className="flex min-w-0 flex-1 flex-col">
        <header className="sticky top-0 z-30 flex items-center gap-3 border-b border-slate-800/80 bg-slate-950/85 px-4 py-3 backdrop-blur-lg sm:px-6">
          <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-gradient-to-br from-cyan-400 to-cyan-700 shadow-md shadow-cyan-950/50 ring-1 ring-cyan-300/30">
            <Bot className="h-5 w-5 text-slate-950" />
          </div>
          <div className="min-w-0 leading-tight">
            <h1 className="text-base font-bold tracking-wide text-slate-100">KEERTHI</h1>
            <p className="text-xs text-slate-400">System Assistant</p>
          </div>
          <span
            className={`ml-1 hidden shrink-0 items-center gap-1.5 rounded-full px-2.5 py-1 text-[11px] font-medium ring-1 sm:inline-flex ${
              wsConnected
                ? 'bg-emerald-500/10 text-emerald-300 ring-emerald-500/30'
                : 'bg-slate-800/60 text-slate-400 ring-slate-700'
            }`}
            title={wsConnected ? 'Live updates connected' : 'Live updates offline'}
          >
            <span
              className={`h-1.5 w-1.5 rounded-full ${
                wsConnected ? 'animate-pulse bg-emerald-400' : 'bg-slate-500'
              }`}
            />
            {wsConnected ? 'live' : 'offline'}
          </span>
          <div className="ml-auto flex shrink-0 items-center gap-2">
            <Button
              variant="ghost"
              onClick={handleReset}
              title="Clear conversation"
              aria-label="Reset conversation"
              className="px-3"
            >
              <RefreshCw className="h-4 w-4" />
              <span className="hidden md:inline">Reset</span>
            </Button>
            <Button
              variant="ghost"
              onClick={() => setSidebarOpen((o) => !o)}
              title="Toggle sidebar"
              aria-label="Toggle sidebar"
              className="px-3"
            >
              {sidebarOpen ? (
                <PanelLeftClose className="h-4 w-4" />
              ) : (
                <PanelLeftOpen className="h-4 w-4" />
              )}
            </Button>
          </div>
        </header>

        <section className="mx-auto flex w-full max-w-3xl flex-1 flex-col gap-4 overflow-y-auto px-4 py-5 sm:px-6">
          {messages.length === 0 ? (
            <EmptyState onSuggest={sendMessage} />
          ) : (
            messages.map((msg, i) => <ChatBubble key={i} msg={msg} />)
          )}
          {pendingToken && !loading && (
            <div className="animate-fade-up flex flex-col items-center gap-2.5 rounded-2xl border border-amber-500/30 bg-amber-950/30 px-4 py-3">
              <p className="text-sm text-slate-300">
                Confirm this safety-sensitive action:{' '}
                <span className="font-semibold text-amber-300">
                  {pendingIntents.join(', ') || 'proceed'}
                </span>
              </p>
              <div className="flex gap-2.5">
                <button
                  type="button"
                  onClick={() => handleConfirm(true)}
                  className="btn rounded-xl bg-amber-600 px-4 py-2 text-sm font-semibold text-white shadow-lg shadow-amber-950/40 hover:bg-amber-500 focus-visible:ring-amber-400/70"
                >
                  Confirm &amp; proceed
                </button>
                <button type="button" onClick={() => handleConfirm(false)} className="btn btn-ghost">
                  Cancel
                </button>
              </div>
            </div>
          )}
          {loading && <TypingIndicator />}
          <div ref={endRef} />
        </section>

        <footer className="border-t border-slate-800/80 px-4 py-4 sm:px-6">
          <form
            onSubmit={(e) => {
              e.preventDefault()
              handleSend()
            }}
            className="mx-auto flex w-full max-w-3xl items-center gap-2 rounded-2xl border border-slate-700/80 bg-slate-900/60 p-2 shadow-lg shadow-black/20 backdrop-blur"
          >
            <Button
              type="button"
              variant="ghost"
              onClick={startListening}
              disabled={loading}
              aria-label={listening ? 'Recording… tap to stop' : 'Mic'}
              title="Voice input"
              className="shrink-0 rounded-xl px-3"
            >
              {listening ? <MicOff className="h-4 w-4 text-red-400" /> : <Mic className="h-4 w-4" />}
              <span className="hidden sm:inline">{listening ? 'Recording…' : 'Mic'}</span>
            </Button>
            <input
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Type a message…"
              className="min-w-0 flex-1 bg-transparent px-2 py-1.5 text-sm text-slate-100 outline-none placeholder:text-slate-500"
            />
            <Button
              type="submit"
              variant="primary"
              disabled={loading || !input.trim()}
              aria-label="Send"
              className="shrink-0 rounded-xl px-4"
            >
              <Send className="h-4 w-4" />
              <span className="hidden sm:inline">Send</span>
            </Button>
          </form>
        </footer>
      </main>

      {sidebarOpen && (
        <div
          className="fixed inset-0 z-40 bg-black/60 backdrop-blur-sm lg:hidden"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      <aside
        className={`fixed inset-y-0 right-0 z-50 flex w-[22rem] max-w-[88vw] flex-col overflow-y-auto border-l border-slate-800/80 bg-slate-950/95 backdrop-blur transition-transform duration-300 ease-in-out lg:static lg:translate-x-0 lg:transition-[width] ${
          sidebarOpen
            ? 'translate-x-0 p-4 lg:w-[22rem]'
            : 'translate-x-full p-4 lg:w-0 lg:translate-x-0 lg:overflow-hidden lg:p-0'
        }`}
      >
        {system && (
          <>
            <div className="mb-4 flex items-center justify-between">
              <h2 className="flex min-w-0 items-center gap-2 text-sm font-semibold text-slate-300">
                <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-lg bg-slate-800 ring-1 ring-slate-700">
                  <Monitor className="h-4 w-4 text-cyan-400" />
                </span>
                <span className="truncate">{system.hostname}</span>
              </h2>
              <span className="shrink-0 text-[11px] text-slate-500">{system.platform}</span>
            </div>

            <div className="mb-2 grid grid-cols-4 gap-2">
              <Gauge label="CPU" value={system.cpu} color="#22d3ee" />
              <Gauge label="RAM" value={system.memoryPercent} color="#a78bfa" />
              <Gauge label="Disk" value={system.diskPercent} color="#34d399" />
              <Gauge label="Battery" value={system.batteryPercent} color="#fbbf24" />
            </div>

            <div className="card mb-4 grid grid-cols-2 gap-x-3 gap-y-1.5 px-3 py-2.5 text-xs text-slate-400">
              <span className="flex items-center gap-1.5">
                <Cpu className="h-3.5 w-3.5 shrink-0 text-slate-500" />
                {system.cores} cores
              </span>
              <span className="flex items-center gap-1.5">
                <Clock className="h-3.5 w-3.5 shrink-0 text-slate-500" />
                up {formatUptime(system.uptime)}
              </span>
              <span className="col-span-2 flex items-center gap-1.5">
                <HardDrive className="h-3.5 w-3.5 shrink-0 text-slate-500" />
                {formatBytes(system.memoryUsed)} / {formatBytes(system.memoryTotal)} RAM ·{' '}
                {formatBytes(system.diskUsed)} / {formatBytes(system.diskTotal)} disk
              </span>
              <span className="col-span-2 text-slate-500">
                {system.platform} · Python {system.python}
              </span>
            </div>

            <Card className="mb-4 p-3">
              <SectionHeader icon={Play} title="Launch App" />
              <div className="flex gap-2">
                <select
                  value={selectedApp}
                  onChange={(e) => setSelectedApp(e.target.value)}
                  className="input min-w-0 flex-1"
                >
                  {KNOWN_APPS.map((app) => (
                    <option key={app} value={app}>
                      {app}
                    </option>
                  ))}
                </select>
                <Button
                  variant="primary"
                  onClick={() => runAction('OPEN_APP', [selectedApp])}
                  disabled={loading}
                  aria-label="Open selected app"
                >
                  Open
                </Button>
              </div>
            </Card>

            <Card className="mb-4 p-3">
              <SectionHeader icon={Volume2} title="Power & Media" />
              <div className="space-y-3">
                <Slider
                  icon={Volume2}
                  value={volume}
                  onChange={setVolume}
                  onCommit={() => runAction('SET_VOLUME', [String(volume)])}
                  ariaLabel="Volume"
                >
                  <button
                    type="button"
                    onClick={() => {
                      setMuted(!muted)
                      runAction('MUTE', [muted ? 'off' : 'on'])
                    }}
                    disabled={loading}
                    className="shrink-0 text-slate-400 transition-colors hover:text-slate-100 disabled:opacity-40"
                    title={muted ? 'Unmute' : 'Mute'}
                  >
                    {muted ? <VolumeX className="h-4 w-4" /> : <Volume2 className="h-4 w-4" />}
                  </button>
                </Slider>
                <Slider
                  icon={Sun}
                  value={brightness}
                  onChange={setBrightness}
                  onCommit={() => runAction('SET_BRIGHTNESS', [String(brightness)])}
                  ariaLabel="Brightness"
                  showValue
                />
                <div className="grid grid-cols-4 gap-1.5 pt-1">
                  <Button
                    variant="soft"
                    onClick={() => runAction('LOCK_SCREEN')}
                    disabled={loading}
                    title="Lock screen"
                    aria-label="Lock screen"
                    className="flex-col gap-0.5 py-2 text-[11px]"
                  >
                    <Lock className="h-4 w-4" />
                    Lock
                  </Button>
                  <Button
                    variant="soft"
                    onClick={() => runAction('SLEEP')}
                    disabled={loading}
                    title="Sleep"
                    aria-label="Sleep"
                    className="flex-col gap-0.5 py-2 text-[11px]"
                  >
                    <Moon className="h-4 w-4" />
                    Sleep
                  </Button>
                  <Button
                    variant="soft"
                    onClick={() => runAction('RESTART')}
                    disabled={loading}
                    title="Restart"
                    aria-label="Restart"
                    className="flex-col gap-0.5 py-2 text-[11px]"
                  >
                    <RefreshCw className="h-4 w-4" />
                    Restart
                  </Button>
                  <Button
                    variant="danger"
                    onClick={() => runAction('SHUTDOWN')}
                    disabled={loading}
                    title="Shut down"
                    aria-label="Shut down"
                    className="flex-col gap-0.5 py-2 text-[11px]"
                  >
                    <Power className="h-4 w-4" />
                    Shut
                  </Button>
                </div>
              </div>
            </Card>

            <Card className="mb-4 p-3">
              <SectionHeader icon={Terminal} title="Run Command" />
              <div className="flex gap-2">
                <input
                  value={command}
                  onChange={(e) => setCommand(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter' && command.trim()) {
                      runCommandNow()
                    }
                  }}
                  placeholder="e.g. echo hello"
                  className="input min-w-0 flex-1"
                />
                <Button onClick={runCommandNow} disabled={loading || !command.trim()}>
                  Run
                </Button>
              </div>
            </Card>

            <Card className="mb-4 p-3">
              <SectionHeader icon={Wifi} title="Browser" />
              <div className="flex gap-2">
                <input
                  value={urlInput}
                  onChange={(e) => setUrlInput(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter' && urlInput.trim()) {
                      openUrl()
                    }
                  }}
                  placeholder="URL or search…"
                  className="input min-w-0 flex-1"
                />
                <Button
                  variant="primary"
                  onClick={openUrl}
                  disabled={loading || !urlInput.trim()}
                  aria-label="Open URL"
                  title="Open URL"
                >
                  Open
                </Button>
                <Button
                  onClick={searchWeb}
                  disabled={loading || !urlInput.trim()}
                  aria-label="Web search"
                  title="Web search"
                >
                  Search
                </Button>
              </div>
            </Card>

            <Card className="mb-4 p-3">
              <SectionHeader icon={FolderOpen} title="Files" tone="amber" />
              <FileBrowser />
            </Card>

            <Card className="mb-4 p-3">
              <SectionHeader icon={Camera} title="Screenshot" tone="violet" />
              <Button variant="soft" className="w-full" onClick={takeScreenshot} disabled={loading}>
                Capture screen
              </Button>
              {screenshot && (
                <img
                  src={screenshot}
                  alt="Screen capture"
                  className="mt-2.5 w-full rounded-xl border border-slate-800"
                />
              )}
            </Card>

            <Card className="mb-4 p-3">
              <SectionHeader icon={Database} title="Processes" tone="violet" />
              <div className="max-h-48 overflow-y-auto">
                <table className="w-full text-xs">
                  <thead className="sticky top-0 z-10 bg-slate-900/95 text-slate-500 backdrop-blur">
                    <tr>
                      <th className="px-2 py-1.5 text-left font-medium">Name</th>
                      <th className="px-2 py-1.5 text-right font-medium">CPU</th>
                      <th className="px-2 py-1.5 text-right font-medium">MEM</th>
                      <th className="px-2 py-1.5" />
                    </tr>
                  </thead>
                  <tbody>
                    {(state?.processes ?? []).map((proc) => (
                      <tr
                        key={proc.pid}
                        className="border-t border-slate-800/60 transition-colors hover:bg-slate-800/40"
                      >
                        <td className="max-w-[8rem] truncate px-2 py-1.5" title={`PID ${proc.pid}`}>
                          {proc.name}
                        </td>
                        <td className="px-2 py-1.5 text-right font-medium text-cyan-300">
                          {proc.cpu}%
                        </td>
                        <td className="px-2 py-1.5 text-right text-slate-300">{proc.memory}%</td>
                        <td className="px-2 py-1.5 text-right">
                          <button
                            type="button"
                            onClick={() => runAction('KILL_PROCESS', [String(proc.pid)])}
                            disabled={loading}
                            className="text-slate-500 transition-colors hover:text-red-400 disabled:opacity-40"
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
            </Card>

            <Card className="mb-4 p-3">
              <SectionHeader icon={AppWindow} title="Windows" tone="violet" />
              <Button variant="soft" className="mb-2 w-full" onClick={loadWindows}>
                Refresh windows
              </Button>
              {windows.length === 0 ? (
                <p className="text-sm text-slate-500">No open windows.</p>
              ) : (
                <ul className="max-h-40 space-y-0.5 overflow-y-auto pr-0.5">
                  {windows.map((w) => (
                    <li
                      key={w.hwnd}
                      className="group flex items-center gap-1.5 rounded-lg px-2 py-1.5 text-xs transition-colors hover:bg-slate-800/50"
                    >
                      <span className="min-w-0 flex-1 truncate text-slate-300" title={w.title}>
                        {w.title}
                      </span>
                      <div className="flex shrink-0 items-center gap-0.5 opacity-70 transition-opacity group-hover:opacity-100">
                        <button
                          type="button"
                          onClick={() => runAction('FOCUS_WINDOW', [w.title])}
                          disabled={loading}
                          className="rounded p-1 text-slate-400 transition-colors hover:text-cyan-300 disabled:opacity-40"
                          title="Focus"
                        >
                          <LayoutGrid className="h-3.5 w-3.5" />
                        </button>
                        <button
                          type="button"
                          onClick={() => runAction('MINIMIZE_WINDOW', [w.title])}
                          disabled={loading}
                          className="rounded p-1 text-slate-400 transition-colors hover:text-amber-300 disabled:opacity-40"
                          title="Minimize"
                        >
                          <Minimize className="h-3.5 w-3.5" />
                        </button>
                        <button
                          type="button"
                          onClick={() => runAction('MAXIMIZE_WINDOW', [w.title])}
                          disabled={loading}
                          className="rounded p-1 text-slate-400 transition-colors hover:text-emerald-300 disabled:opacity-40"
                          title="Maximize"
                        >
                          <Maximize className="h-3.5 w-3.5" />
                        </button>
                        <button
                          type="button"
                          onClick={() => runAction('CLOSE_WINDOW', [w.title])}
                          disabled={loading}
                          className="rounded p-1 text-slate-400 transition-colors hover:text-red-300 disabled:opacity-40"
                          title="Close"
                        >
                          <X className="h-3.5 w-3.5" />
                        </button>
                      </div>
                    </li>
                  ))}
                </ul>
              )}
            </Card>

            <Card className="mb-4 p-3">
              <SectionHeader icon={CheckCircle2} title="Tasks" tone="emerald" />
              {state?.tasks.length === 0 ? (
                <p className="text-sm text-slate-500">No tasks.</p>
              ) : (
                <ul className="space-y-1.5 text-sm">
                  {state?.tasks.map((task) => (
                    <li key={task} className="flex items-center gap-2 text-slate-300">
                      <span className="h-1.5 w-1.5 shrink-0 rounded-full bg-cyan-500 shadow-[0_0_6px_rgba(34,211,238,0.8)]" />
                      {task}
                    </li>
                  ))}
                </ul>
              )}
            </Card>

            <Card className="mb-4 p-3">
              <SectionHeader icon={Clock} title="Timers" tone="amber" />
              {state?.timers.length === 0 ? (
                <p className="text-sm text-slate-500">No timers.</p>
              ) : (
                <ul className="space-y-1.5 text-sm">
                  {state?.timers.map((timer, i) => (
                    <li key={i} className="flex items-center justify-between gap-2">
                      <span className="flex min-w-0 items-center gap-2 text-slate-300">
                        <span className="h-1.5 w-1.5 shrink-0 rounded-full bg-amber-500 shadow-[0_0_6px_rgba(245,158,11,0.8)]" />
                        <span className="truncate">{timer.label}</span>
                      </span>
                      <span className="shrink-0 font-mono text-xs text-amber-300">
                        {formatDuration(timer.due * 1000 - now)}
                      </span>
                    </li>
                  ))}
                </ul>
              )}
            </Card>
          </>
        )}
      </aside>
    </div>
  )
}
