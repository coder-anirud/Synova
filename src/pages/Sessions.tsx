import { useEffect, useMemo, useState } from 'react'
import { DemoBadge, Panel } from '../components/UI'

interface LogItem { time: string; label: string; detail: string }

function formatTime(total: number) { const minutes = Math.floor(total / 60).toString().padStart(2, '0'); const seconds = (total % 60).toString().padStart(2, '0'); return `${minutes}:${seconds}` }

export function Sessions() {
  const [status, setStatus] = useState<'ready' | 'running' | 'paused' | 'complete'>('ready')
  const [seconds, setSeconds] = useState(0)
  const [logs, setLogs] = useState<LogItem[]>([])
  const [mode, setMode] = useState('Guided intention test')
  useEffect(() => {
    if (status !== 'running') return
    const timer = window.setInterval(() => setSeconds((value) => value + 1), 1000)
    return () => window.clearInterval(timer)
  }, [status])
  const addLog = (label: string, detail: string) => setLogs((current) => [{ time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' }), label, detail }, ...current])
  const metrics = useMemo(() => ({ trials: Math.floor(seconds / 8), correct: Math.floor(seconds / 10), commands: Math.floor(seconds / 13), falseActivations: Math.floor(seconds / 47) }), [seconds])
  const start = () => { setStatus('running'); addLog('Session started', `${mode} · Demo mode`) }
  const end = () => { setStatus('complete'); addLog('Session ended', `Duration ${formatTime(seconds)}`); localStorage.setItem('synova-last-session', JSON.stringify({ seconds, mode, completedAt: new Date().toISOString() })) }
  return <div className="page">
    <header className="page-heading"><div><h1>Training sessions</h1><p>Run a structured test and review what happened.</p></div><DemoBadge /></header>
    <Panel className="session-console">
      <div className="session-setup"><label>Testing mode<select value={mode} onChange={(e) => setMode(e.target.value)} disabled={status === 'running'}><option>Guided intention test</option><option>Classifier-only review</option><option>Manual glove practice</option></select></label><div className="session-timer"><span>{status === 'running' ? 'Session in progress' : status === 'paused' ? 'Session paused' : status === 'complete' ? 'Session complete' : 'Ready to begin'}</span><strong>{formatTime(seconds)}</strong></div><div className="session-actions">{status === 'ready' || status === 'complete' ? <button className="button" onClick={() => { if (status === 'complete') { setSeconds(0); setLogs([]) }; start() }}>Start session</button> : <><button className="button button--secondary" onClick={() => { const next = status === 'paused' ? 'running' : 'paused'; setStatus(next); addLog(next === 'paused' ? 'Session paused' : 'Session resumed', 'Timer updated') }}>{status === 'paused' ? 'Resume' : 'Pause'}</button><button className="button button--danger" onClick={end}>End session</button></>}</div></div>
      <div className="session-metrics"><div><span>Total trials</span><strong>{metrics.trials}</strong></div><div><span>Correct classifications</span><strong>{metrics.correct}</strong></div><div><span>Commands sent</span><strong>{metrics.commands}</strong></div><div><span>False activations</span><strong>{metrics.falseActivations}</strong></div></div>
    </Panel>
    <div className="two-column two-column--wide">
      <Panel title={<h2>Session activity</h2>} action={<button className="text-button" disabled={status !== 'running'} onClick={() => addLog('Open intention detected', '87% simulated confidence')}>Add demo event</button>}>
        <div className="event-log">{logs.length === 0 ? <div className="empty-state"><span>Activity will appear here after the session starts.</span></div> : logs.map((log, index) => <div key={`${log.time}-${index}`}><time>{log.time}</time><span><strong>{log.label}</strong><small>{log.detail}</small></span></div>)}</div>
      </Panel>
      <Panel title={<h2>About these results</h2>}><div className="notice"><strong>Demo data is kept separate</strong><p>These counts demonstrate the interface only. Classifier performance and physical movement execution are different measurements and should be reported separately.</p></div></Panel>
    </div>
  </div>
}
