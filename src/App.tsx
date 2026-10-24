import { lazy, Suspense, useEffect, useState } from 'react'
import { Brand } from './components/Brand'
import { Sidebar } from './components/Sidebar'
import { Dashboard } from './pages/Dashboard'
import { useGlove } from './hardware/useGlove'
import { useMuse } from './hardware/useMuse'
import type { AppSettings, HandState, PageId } from './types'

const Analytics = lazy(() => import('./pages/Analytics').then((module) => ({ default: module.Analytics })))
const Calibration = lazy(() => import('./pages/Calibration').then((module) => ({ default: module.Calibration })))
const GloveControl = lazy(() => import('./pages/GloveControl').then((module) => ({ default: module.GloveControl })))
const Sessions = lazy(() => import('./pages/Sessions').then((module) => ({ default: module.Sessions })))
const Settings = lazy(() => import('./pages/Settings').then((module) => ({ default: module.Settings })))
const Signals = lazy(() => import('./pages/Signals').then((module) => ({ default: module.Signals })))

const defaultSettings: AppSettings = { confidenceThreshold: 80, sustainedDetection: 750, cooldown: 2000, signalThreshold: 65, reduceMotion: false, highContrast: false }
const titles: Record<PageId, string> = { dashboard: 'Dashboard', signals: 'Brain Signals', calibration: 'Calibration', glove: 'Glove Control', sessions: 'Training Sessions', analytics: 'Progress & Analytics', settings: 'Settings' }
const mobileTabs: Array<{ id: PageId; label: string }> = [
  { id: 'dashboard', label: 'Home' },
  { id: 'signals', label: 'Signals' },
  { id: 'glove', label: 'Glove' },
  { id: 'sessions', label: 'Sessions' },
  { id: 'settings', label: 'Settings' },
]

function getInitialPage(): PageId {
  const hash = window.location.hash.replace('#/', '') as PageId
  return Object.hasOwn(titles, hash) ? hash : 'dashboard'
}

export default function App() {
  const [page, setPage] = useState<PageId>(getInitialPage)
  const [menuOpen, setMenuOpen] = useState(false)
  const [handState, setHandState] = useState<HandState>('REST')
  const [armed, setArmed] = useState(false)
  const [gloveMode, setGloveMode] = useState<'demo' | 'hardware'>(() => localStorage.getItem('synova-glove-mode') === 'hardware' ? 'hardware' : 'demo')
  const glove = useGlove()
  const muse = useMuse()
  const shownHandState: HandState = gloveMode === 'hardware'
    ? glove.status.stopped ? 'STOPPED' : ['OPEN', 'CLOSE', 'REST'].includes(glove.status.command) ? glove.status.command as HandState : 'REST'
    : handState
  const changeGloveMode = (mode: 'demo' | 'hardware') => {
    if (gloveMode === 'hardware' && mode === 'demo' && glove.status.connected) glove.send('stop')
    setGloveMode(mode)
    localStorage.setItem('synova-glove-mode', mode)
    setArmed(false)
  }
  const [settings, setSettings] = useState<AppSettings>(() => {
    try { return { ...defaultSettings, ...JSON.parse(localStorage.getItem('synova-settings') || '{}') } } catch { return defaultSettings }
  })

  useEffect(() => {
    const onHash = () => setPage(getInitialPage())
    window.addEventListener('hashchange', onHash)
    return () => window.removeEventListener('hashchange', onHash)
  }, [])
  useEffect(() => { document.title = `${titles[page]} · Synova`; window.scrollTo({ top: 0, behavior: settings.reduceMotion ? 'auto' : 'smooth' }) }, [page, settings.reduceMotion])
  const navigate = (next: PageId) => { setPage(next); window.history.pushState(null, '', `#/${next}`) }

  return <div className={`app-shell ${settings.highContrast ? 'high-contrast' : ''} ${settings.reduceMotion ? 'reduce-motion' : ''}`}>
    <a className="skip-link" href="#main-content">Skip to main content</a>
    <header className="desktop-toolbar">
      <div className="desktop-toolbar__identity">
        <span className="window-controls" aria-hidden="true"><i /><i /><i /></span>
        <Brand compact />
        <span className="desktop-toolbar__tagline">Where Thought Becomes Motion.</span>
      </div>
      <div className="desktop-toolbar__actions" aria-label="Application actions">
        <button className="toolbar-primary" onClick={() => navigate('sessions')}>Start session</button>
        <button onClick={() => { if (gloveMode === 'hardware') glove.send('stop'); else { setHandState('STOPPED'); setArmed(false) } }}>Stop</button>
        <button onClick={() => navigate('sessions')}>Sessions</button>
        <button onClick={() => navigate('analytics')}>Progress</button>
        <button onClick={() => navigate('settings')} aria-label="Open settings">Settings</button>
      </div>
    </header>
    <div className="mobile-header"><Brand compact /><button className="menu-button" onClick={() => setMenuOpen(true)} aria-label="Open navigation">Menu</button></div>
    <Sidebar page={page} onNavigate={navigate} open={menuOpen} onClose={() => setMenuOpen(false)} />
    {menuOpen && <button className="scrim" onClick={() => setMenuOpen(false)} aria-label="Close navigation" />}
    <main id="main-content" className={`app-main app-main--${page}`}>
      <Suspense fallback={<div className="route-loading" role="status">Opening workspace…</div>}>
        {page === 'dashboard' && <Dashboard handState={shownHandState} onHandState={setHandState} onStartSession={() => navigate('sessions')} gloveMode={gloveMode} gloveStatus={glove.status} muse={muse} />}
        {page === 'signals' && <Signals muse={muse} />}
        {page === 'calibration' && <Calibration muse={muse} />}
        {page === 'glove' && <GloveControl state={shownHandState} onState={setHandState} armed={armed} onArmed={setArmed} mode={gloveMode} onMode={changeGloveMode} hardware={glove} />}
        {page === 'sessions' && <Sessions />}
        {page === 'analytics' && <Analytics />}
        {page === 'settings' && <Settings settings={settings} onSettings={setSettings} muse={muse} gloveMode={gloveMode} gloveStatus={glove.status} />}
      </Suspense>
    </main>
    <nav className="mobile-tab-bar" aria-label="Quick navigation">
      {mobileTabs.map((tab) => <button key={tab.id} className={page === tab.id ? 'is-active' : ''} onClick={() => navigate(tab.id)} aria-current={page === tab.id ? 'page' : undefined}><span>{tab.label}</span></button>)}
    </nav>
  </div>
}
