import { HandVisual } from '../components/HandVisual'
import { Panel } from '../components/UI'
import type { HandState } from '../types'
import type { GloveStatus } from '../hardware/useGlove'

type GloveHardware = { available: boolean; status: GloveStatus; send: (action: string, id?: string) => void }

export function GloveControl({ state, onState, armed, onArmed, mode, onMode, hardware }: {
  state: HandState
  onState: (state: HandState) => void
  armed: boolean
  onArmed: (armed: boolean) => void
  mode: 'demo' | 'hardware'
  onMode: (mode: 'demo' | 'hardware') => void
  hardware: GloveHardware
}) {
  const real = mode === 'hardware'
  const status = hardware.status
  const stopped = real ? status.stopped : state === 'STOPPED'
  const isArmed = real ? status.armed : armed
  const canMove = real ? status.connected && status.ready && status.armed && !status.stopped : armed && !stopped
  const issueCommand = (next: 'OPEN' | 'CLOSE' | 'REST') => {
    if (!canMove) return
    if (real) hardware.send(next.toLowerCase())
    else onState(next)
  }
  const toggleArm = () => {
    if (real) hardware.send(isArmed ? 'disarm' : 'arm')
    else onArmed(!armed)
  }
  const stop = () => {
    if (real) hardware.send('stop')
    else { onState('STOPPED'); onArmed(false) }
  }
  const reset = () => {
    if (real) hardware.send('reset')
    else onState('REST')
  }

  return <div className="page glove-page">
    <header className="page-heading"><div><h1>Glove control</h1><p>Connect the glove, check its status, then choose a movement.</p></div></header>

    <div className="glove-mode" role="group" aria-label="Glove mode">
      <button className={mode === 'demo' ? 'is-active' : ''} onClick={() => onMode('demo')}>Demo</button>
      <button className={mode === 'hardware' ? 'is-active' : ''} onClick={() => onMode('hardware')}>Real glove</button>
    </div>

    {real && <Panel className="glove-connection" title={<h2>Connect your glove</h2>}>
      {!hardware.available ? <p>Bluetooth glove control requires Synova on a physical iPhone.</p> : <>
        <p>Turn on the ESP32-S3 glove, then tap “Find glove.” Keep the glove off your hand during setup.</p>
        <div className="button-row">
          <button className="button" onClick={() => hardware.send('scan')} disabled={status.scanning}>{status.scanning ? 'Looking…' : 'Find glove'}</button>
          {status.connected && <button className="button button--secondary" onClick={() => hardware.send('disconnect')}>Disconnect</button>}
        </div>
        {status.devices.length > 0 && !status.connected && <div className="glove-device-list">{status.devices.map((device) => <button key={device.id} onClick={() => hardware.send('connect', device.id)}>{device.name}<span>Connect</span></button>)}</div>}
        <p className="glove-message" role="status">{status.message}</p>
      </>}
    </Panel>}

    <div className={`safety-banner ${stopped ? 'is-stopped' : ''}`} role="status"><div><div><strong>{stopped ? 'Emergency stop is active' : isArmed ? 'Controls are armed' : 'Controls are locked'}</strong><span>{stopped ? 'Movement is locked until you reset the stop.' : real && !status.ready ? 'Connect a ready glove before arming.' : isArmed ? 'Keep hands clear while testing movement.' : 'Arm controls before sending a command.'}</span></div></div></div>

    <div className="glove-layout">
      <Panel className="glove-preview" title={<h2>Commanded position</h2>}><HandVisual state={state} /><div className="current-command"><span>Current command</span><strong>{state}</strong></div></Panel>
      <div className="control-stack">
        <Panel title={<h2>Manual controls</h2>}>
          <div className="control-mode"><span>Control mode</span><strong>{real ? 'Real glove · Bluetooth' : 'Demo · No movement'}</strong></div>
          <button className={`arm-control ${isArmed ? 'is-armed' : ''}`} disabled={stopped || (real && !status.ready)} onClick={toggleArm}><span><strong>{isArmed ? 'Disarm controls' : 'Arm controls'}</strong><small>{isArmed ? 'Lock movement commands' : 'Required before movement'}</small></span></button>
          <div className="command-grid">
            <button disabled={!canMove} onClick={() => issueCommand('OPEN')}>Open hand</button>
            <button disabled={!canMove} onClick={() => issueCommand('CLOSE')}>Close hand</button>
            <button disabled={!canMove} onClick={() => issueCommand('REST')}>Rest</button>
          </div>
        </Panel>
        <Panel className="emergency-panel">
          {!stopped ? <button className="emergency-button" onClick={stop}>Emergency stop<span>Lock movement immediately</span></button> : <button className="reset-button" onClick={reset} disabled={real && !status.connected}>Reset emergency stop<span>Check the glove and surrounding area first</span></button>}
        </Panel>
        <Panel title={<h2>Connection details</h2>}><div className="check-list compact">
          <div><span>Glove connection</span><strong>{real ? status.connected ? 'Connected' : 'Disconnected' : 'Demo only'}</strong></div>
          <div><span>Device readiness</span><strong>{real ? status.ready ? 'Ready' : 'Locked' : 'Simulated'}</strong></div>
          <div><span>Last command</span><strong>{real ? status.command : state}</strong></div>
          <div><span>Last acknowledgment</span><strong>{real ? status.lastAcknowledgedAt ? new Date(status.lastAcknowledgedAt).toLocaleTimeString() : 'None' : 'Not applicable'}</strong></div>
        </div></Panel>
      </div>
    </div>
    <p className="safety-copy">A command acknowledgment confirms the controller received it; it does not measure finger position. Test the powered glove on a bench before anyone wears it.</p>
  </div>
}
