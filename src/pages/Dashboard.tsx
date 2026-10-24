import { HandVisual } from '../components/HandVisual'
import { LiveEEG } from '../components/LiveEEG'
import { Panel } from '../components/UI'
import type { HandState } from '../types'
import type { GloveStatus } from '../hardware/useGlove'
import type { MuseController } from '../hardware/useMuse'

export function Dashboard({ handState, onHandState, onStartSession, gloveMode, gloveStatus, muse }: { handState: HandState; onHandState: (state: HandState) => void; onStartSession: () => void; gloveMode: 'demo' | 'hardware'; gloveStatus: GloveStatus; muse: MuseController }) {
  const movementLabel = handState === 'STOPPED' ? 'Stopped' : handState === 'OPEN' ? 'Open hand' : handState === 'CLOSE' ? 'Close hand' : 'Rest'

  return (
    <div className="page dashboard-page">
      <div className="dashboard-workspace">
        <header className="page-heading dashboard-heading">
          <div><h1>Welcome to Synova</h1><p>Explore the demo, then connect your devices when they arrive.</p></div>
          <span className="research-note">Research prototype · Not a medical device</span>
        </header>
        <button className="primary-action" onClick={onStartSession}>Start guided session</button>

        <div className="system-overview" aria-label="System connections">
          <div className="system-item"><div><span>Muse 2 headset</span><strong className={muse.status?.connected ? '' : 'is-muted'}>{muse.status?.connected ? 'Connected via Mac' : 'Not connected'}</strong><small>{muse.status?.connected ? `${muse.status.sample_rate} samples per second` : 'Demo signals shown below'}</small></div></div>
          <div className="system-divider" />
          <div className="system-item"><div><span>Robotic glove</span><strong className={gloveMode === 'hardware' && gloveStatus.ready ? '' : 'is-muted'}>{gloveMode === 'demo' ? 'Demo mode' : gloveStatus.ready ? 'Connected' : 'Not connected'}</strong><small>{gloveMode === 'hardware' ? gloveStatus.message : 'No physical movement'}</small></div></div>
          <div className="system-divider" />
          <div className="system-item"><div><span>Brain signal source</span><strong className={muse.status?.connected ? '' : 'is-muted'}>{muse.status?.connected ? 'Live Muse 2' : 'Simulated'}</strong><small>{muse.status?.connected ? 'Monitoring only · No automatic movement' : 'Live Muse data is not active'}</small></div></div>
        </div>

        <LiveEEG muse={muse.status} />

        <Panel className="activity-console" title={<h2>Before you begin</h2>}>
          <div className="activity-list">
            <div className="activity-row"><strong>Muse 2</strong><span>{muse.status?.connected ? 'Live signal monitoring is available.' : 'Connect the Mac bridge in Settings when the headset arrives.'}</span></div>
            <div className="activity-row"><strong>Glove</strong><span>{gloveMode === 'hardware' ? gloveStatus.message : 'Try the controls safely in Demo mode.'}</span></div>
            <div className="activity-row"><strong>Movement</strong><span>Brain signals do not move the glove automatically. Use manual controls after bench testing.</span></div>
          </div>
        </Panel>
      </div>

      <aside className="intention-inspector" aria-label="Movement intention inspector">
        <header><h2>Movement intention</h2></header>
        <div className="inspector-summary"><strong>{movementLabel}</strong><div><b>{gloveMode === 'demo' ? 'Demo' : 'Manual'}</b><span>command</span></div></div>
        <HandVisual state={handState} />
        {gloveMode === 'demo' && <div className="segmented-control" aria-label="Demo commanded position">
          {(['OPEN', 'CLOSE', 'REST'] as HandState[]).map((state) => <button key={state} className={handState === state ? 'is-active' : ''} onClick={() => onHandState(state)}>{state === 'OPEN' ? 'Open' : state === 'CLOSE' ? 'Close' : 'Rest'}</button>)}
        </div>}
        <section className="inspector-details">
          <h3>Detected movement details</h3>
          <dl><div><dt>Command</dt><dd>{movementLabel}</dd></div><div><dt>Control</dt><dd>{gloveMode === 'demo' ? 'Demo only' : 'Manual'}</dd></div><div><dt>Brain signals</dt><dd>{muse.status?.connected ? 'Live Muse 2' : 'Simulated'}</dd></div><div><dt>Glove feedback</dt><dd>{gloveMode === 'hardware' ? 'Command acknowledgment only' : 'None'}</dd></div></dl>
        </section>
      </aside>
    </div>
  )
}
