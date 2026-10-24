import { useEffect, useState } from 'react'

export interface GloveDevice { id: string; name: string }
export interface GloveStatus {
  bluetooth: 'unavailable' | 'unsupported' | 'ready'
  scanning: boolean
  devices: GloveDevice[]
  connected: boolean
  ready: boolean
  armed: boolean
  stopped: boolean
  command: string
  lastAcknowledgedAt: string | null
  message: string
}

const initial: GloveStatus = {
  bluetooth: 'unavailable', scanning: false, devices: [], connected: false,
  ready: false, armed: false, stopped: false, command: 'REST',
  lastAcknowledgedAt: null, message: 'Connect a glove to begin.',
}

export function useGlove() {
  const [status, setStatus] = useState<GloveStatus>(initial)
  const available = Boolean(window.webkit?.messageHandlers?.synovaGlove)

  useEffect(() => {
    if (!available) return
    const update = (event: Event) => setStatus((event as CustomEvent<GloveStatus>).detail)
    window.addEventListener('synova-glove', update)
    window.webkit?.messageHandlers?.synovaGlove?.postMessage({ action: 'status' })
    return () => window.removeEventListener('synova-glove', update)
  }, [available])

  const send = (action: string, id?: string) => {
    window.webkit?.messageHandlers?.synovaGlove?.postMessage(id ? { action, id } : { action })
  }

  return { available, status, send }
}
