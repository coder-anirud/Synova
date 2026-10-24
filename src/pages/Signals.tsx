import { useState } from 'react'
import { LiveEEG } from '../components/LiveEEG'
import { DemoBadge, Panel } from '../components/UI'
import type { MuseController } from '../hardware/useMuse'

export function Signals({ muse }: { muse: MuseController }) {
  const live = Boolean(muse.status?.connected)
  const [recordingLabel, setRecordingLabel] = useState('signal_check')
  const recording = muse.status?.recording
  const exportData = () => {
    const current = muse.status
    if (!current?.connected) return
    const count = Math.min(...current.samples.map(row => row.length))
    const lines = ['sample,TP9,AF7,AF8,TP10']
    for (let index = 0; index < count; index++) lines.push([index, ...current.samples.map(row => row[row.length - count + index])].join(','))
    const blob = new Blob([lines.join('\n')], { type: 'text/csv' })
    const href = URL.createObjectURL(blob)
    const link = document.createElement('a'); link.href = href; link.download = 'synova-muse-latest.csv'; link.click(); window.setTimeout(() => URL.revokeObjectURL(href), 1000)
  }
  return <div className="page">
    <header className="page-heading"><div><h1>Brain signals</h1><p>See a simple preview, or connect Muse 2 through your Mac.</p></div>{!live && <DemoBadge />}</header>
    <div className="toolbar">
      <div className="toolbar__status"><strong>{live ? 'Muse 2 connected through Mac' : muse.enabled ? 'Waiting for Muse 2' : 'Showing a demo preview'}</strong><span>{live ? `${muse.status?.sample_rate} samples per second · four EEG channels` : muse.message}</span></div>
      <div className="toolbar__actions">
        <button className="button button--secondary" onClick={exportData} disabled={!live}>Export latest samples</button>
      </div>
    </div>
    <LiveEEG expanded muse={muse.status} />
    <Panel className="recording-panel" title={<div className="title-row"><h2>Save a quick EEG check</h2>{recording?.active && <span className="live-badge">Recording</span>}</div>}>
      <div className="recording-controls"><label>File label<select value={recordingLabel} disabled={recording?.active} onChange={(event) => setRecordingLabel(event.target.value)}><option value="signal_check">General signal check</option><option value="rest">Rest</option><option value="imagine_open">Imagine opening</option><option value="imagine_close">Imagine closing</option></select></label>{recording?.active ? <button className="button button--danger" disabled={muse.busy} onClick={muse.stopRecording}>Stop and save</button> : <button className="button" disabled={!live || muse.busy} onClick={() => muse.startRecording(recordingLabel)}>Start recording</button>}</div>
      <p className="recording-note">{recording?.active ? `${recording.rows.toLocaleString()} samples saved so far. Quick recordings stop automatically after 10 minutes.` : muse.status?.last_recording ? `Last saved on the Mac: ${muse.status.last_recording.name} · ${muse.status.last_recording.rows.toLocaleString()} samples` : 'Quick CSV files are saved in Documents/Synova Recordings on the Mac. Record at least 6 seconds for a labeled trial; use the randomized Mac recorder for model evaluation.'}</p>
    </Panel>
    <Panel title={<h2>About these signals</h2>}><div className="check-list signal-notes">
      <div><span>Source</span><strong>{live ? 'Muse 2 via Mac bridge' : 'Simulated preview'}</strong></div>
      <div><span>Display</span><strong>Auto-scaled recent samples</strong></div>
      <div><span>Movement detection</span><strong>Not trained or enabled</strong></div>
      <div><span>Glove control</span><strong>Manual only</strong></div>
    </div></Panel>
  </div>
}
