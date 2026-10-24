import { useEffect, useRef, useState } from 'react'

export interface MuseStatus {
  bridge_version?: string
  state?: 'starting' | 'setup_needed' | 'searching' | 'connected' | 'live' | 'retrying'
  connected: boolean
  sample_rate: number
  channels: string[]
  samples: number[][]
  message: string
  captured_at?: number
  sample_age?: number | null
  uptime_seconds?: number
  recording?: { active: boolean; label: string | null; name: string | null; rows: number }
  last_recording?: { active?: boolean; label: string; name: string; rows: number } | null
}

interface MuseReply { id: string; status?: MuseStatus; error?: string }
type MuseAction = 'status' | 'startRecording' | 'stopRecording'

declare global {
  interface Window {
    webkit?: { messageHandlers?: {
      synovaGlove?: { postMessage: (message: Record<string, string>) => void }
      synovaMuse?: { postMessage: (message: Record<string, string>) => void }
    } }
  }
}

export function useMuse() {
  const [host, setHost] = useState(() => localStorage.getItem('synova-muse-host') || '')
  const [token, setToken] = useState(() => localStorage.getItem('synova-muse-token') || '')
  const [enabled, setEnabled] = useState(() => Boolean(localStorage.getItem('synova-muse-host') && localStorage.getItem('synova-muse-token') && localStorage.getItem('synova-muse-auto') !== 'false'))
  const [status, setStatus] = useState<MuseStatus | null>(null)
  const [message, setMessage] = useState(enabled ? 'Reconnecting to the Mac companion…' : 'Muse 2 is not connected.')
  const [busy, setBusy] = useState(false)
  const request = useRef(0)
  const pendingSince = useRef(0)
  const available = Boolean(window.webkit?.messageHandlers?.synovaMuse)

  useEffect(() => {
    const onReply = (event: Event) => {
      const reply = (event as CustomEvent<MuseReply>).detail
      if (reply.id !== String(request.current)) return
      pendingSince.current = 0
      setBusy(false)
      if (reply.error) { setStatus(null); setMessage(reply.error); return }
      const next = reply.status
      if (!next || !Array.isArray(next.samples) || !Array.isArray(next.channels)) {
        setStatus(null); setMessage('The Mac companion response is incomplete.'); return
      }
      setStatus(next)
      setMessage(next.message)
    }
    window.addEventListener('synova-muse', onReply)
    return () => window.removeEventListener('synova-muse', onReply)
  }, [])

  const send = (action: MuseAction, label?: string) => {
    if (!available || !enabled) return false
    if (pendingSince.current && Date.now() - pendingSince.current < 4000) return false
    request.current += 1
    pendingSince.current = Date.now()
    if (action !== 'status') setBusy(true)
    window.webkit?.messageHandlers?.synovaMuse?.postMessage({ action, host, token, id: String(request.current), ...(label ? { label } : {}) })
    return true
  }

  useEffect(() => {
    if (!enabled || !available) return
    const poll = () => send('status')
    poll()
    const interval = window.setInterval(poll, 1000)
    return () => { window.clearInterval(interval); pendingSince.current = 0 }
  }, [enabled, available, host, token])

  const connect = (nextHost: string, nextToken: string) => {
    const cleanHost = nextHost.trim()
    const cleanToken = nextToken.trim()
    localStorage.setItem('synova-muse-host', cleanHost)
    localStorage.setItem('synova-muse-token', cleanToken)
    localStorage.setItem('synova-muse-auto', 'true')
    setHost(cleanHost)
    setToken(cleanToken)
    setStatus(null)
    setMessage('Checking the Mac companion…')
    setEnabled(true)
  }
  const disconnect = () => {
    localStorage.setItem('synova-muse-auto', 'false')
    setEnabled(false)
    setStatus(null)
    setMessage('Muse 2 is not connected.')
    setBusy(false)
  }

  const startRecording = (label: string) => send('startRecording', label)
  const stopRecording = () => send('stopRecording')

  return { available, enabled, status, message, host, token, busy, connect, disconnect, startRecording, stopRecording }
}

export type MuseController = ReturnType<typeof useMuse>
