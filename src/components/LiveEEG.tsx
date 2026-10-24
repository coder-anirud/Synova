import { useEffect, useMemo, useState } from 'react'
import { DemoBadge, Panel } from './UI'
import type { MuseStatus } from '../hardware/useMuse'

const channels = [
  { name: 'TP9', color: '#1677ff', phase: 0.1 },
  { name: 'AF7', color: '#13a45b', phase: 1.4 },
  { name: 'AF8', color: '#7f4cff', phase: 2.6 },
  { name: 'TP10', color: '#ef7d00', phase: 4.1 },
]

function createSignal(index: number, tick: number) {
  return Array.from({ length: 74 }, (_, i) => {
    const noise = Math.sin((i + tick * 2) * (1.7 + index * .13)) * 3.4 + Math.sin((i + tick) * .43 + channels[index].phase) * 6
    const pulse = Math.sin((i + tick * 3) * .13 + index) * 4
    return 32 + noise + pulse
  })
}

export function LiveEEG({ expanded = false, muse }: { expanded?: boolean; muse?: MuseStatus | null }) {
  const [tick, setTick] = useState(0)
  const [enabled, setEnabled] = useState<Record<string, boolean>>(() => Object.fromEntries(channels.map(c => [c.name, true])))
  useEffect(() => {
    const timer = window.setInterval(() => setTick((value) => value + 1), 520)
    return () => window.clearInterval(timer)
  }, [])
  const simulated = useMemo(() => channels.map((_, i) => createSignal(i, tick)), [tick])
  const isLive = Boolean(muse?.connected && muse.samples.length >= 4 && muse.samples.every(row => row.length > 1))
  const signals = isLive ? channels.map((_, index) => {
    const row = muse!.samples[index].slice(-74)
    const center = row.reduce((sum, value) => sum + value, 0) / row.length
    const peak = Math.max(20, ...row.map(value => Math.abs(value - center)))
    return Array.from({ length: 74 }, (_, point) => {
      const value = row[Math.min(row.length - 1, Math.floor(point * row.length / 74))]
      return Math.max(3, Math.min(61, 32 - (value - center) / peak * 25))
    })
  }) : simulated

  return (
    <Panel className={`eeg-panel ${expanded ? 'eeg-panel--expanded' : ''}`} title={<div className="title-row"><h2>{isLive ? 'Muse 2 signals' : 'Brain signal preview'}</h2>{isLive ? <span className="live-badge">Live from Muse 2</span> : <DemoBadge />}</div>}>
      <div className="eeg-grid">
        {channels.map((channel, index) => {
          const points = signals[index].map((value, i) => `${i * (640 / 73)},${value}`).join(' ')
          return (
            <div className="eeg-row" key={channel.name}>
              <button className={`channel-toggle ${enabled[channel.name] ? 'is-on' : ''}`} onClick={() => setEnabled((current) => ({ ...current, [channel.name]: !current[channel.name] }))} style={{ '--channel': channel.color } as React.CSSProperties}>
                <span><strong>{channel.name}</strong><small>{isLive ? 'EEG' : 'Demo'}</small></span>
              </button>
              <div className="eeg-wave">
                <svg preserveAspectRatio="none" viewBox="0 0 640 64" aria-label={`${channel.name} ${isLive ? 'live' : 'simulated'} EEG waveform, auto-scaled`}>
                  <path className="grid-line" d="M0 32H640M160 0V64M320 0V64M480 0V64" />
                  {enabled[channel.name] && <polyline points={points} fill="none" stroke={channel.color} strokeWidth="1.5" vectorEffect="non-scaling-stroke" />}
                </svg>
              </div>
            </div>
          )
        })}
        <div className="eeg-axis"><span>Recent samples · auto-scaled</span><span>Now</span></div>
      </div>
    </Panel>
  )
}
