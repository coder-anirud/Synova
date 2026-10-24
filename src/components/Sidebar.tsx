import type { PageId } from '../types'

const items: Array<{ id: PageId; label: string }> = [
  { id: 'dashboard', label: 'Home' },
  { id: 'signals', label: 'Brain signals' },
  { id: 'calibration', label: 'Calibration' },
  { id: 'glove', label: 'Glove control' },
  { id: 'sessions', label: 'Training sessions' },
  { id: 'analytics', label: 'Progress' },
  { id: 'settings', label: 'Settings' },
]

export function Sidebar({ page, onNavigate, open, onClose }: { page: PageId; onNavigate: (page: PageId) => void; open: boolean; onClose: () => void }) {
  return (
    <aside className={`sidebar ${open ? 'is-open' : ''}`}>
      <button className="sidebar__close" onClick={onClose} aria-label="Close navigation">Close</button>
      <nav className="sidebar__nav" aria-label="Primary navigation">
        {items.map((item) => <button key={item.id} className={page === item.id ? 'is-active' : ''} onClick={() => { onNavigate(item.id); onClose() }}><span>{item.label}</span></button>)}
      </nav>
      <div className="sidebar__status">
        <span className="eyebrow">System status</span>
        <div className="status-line"><div><strong>Demo mode</strong><small>Simulation adapter active</small></div></div>
        <div className="status-line"><div><strong>4 EEG channels</strong><small>Streaming simulated data</small></div></div>
        <div className="prototype-note">Research prototype · Not a medical device</div>
      </div>
    </aside>
  )
}
