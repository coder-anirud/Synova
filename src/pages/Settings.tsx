import { useState } from 'react'
import { Panel, Toggle } from '../components/UI'
import type { AppSettings } from '../types'
import type { MuseController } from '../hardware/useMuse'
import type { GloveStatus } from '../hardware/useGlove'

export function Settings({ settings, onSettings, muse, gloveMode, gloveStatus }: { settings: AppSettings; onSettings: (settings: AppSettings) => void; muse: MuseController; gloveMode: 'demo' | 'hardware'; gloveStatus: GloveStatus }) {
  const [saved, setSaved] = useState(false)
  const [museHost, setMuseHost] = useState(muse.host)
  const [museKey, setMuseKey] = useState(muse.token)
  const update = <K extends keyof AppSettings>(key: K, value: AppSettings[K]) => { onSettings({ ...settings, [key]: value }); setSaved(false) }
  const save = () => { localStorage.setItem('synova-settings', JSON.stringify(settings)); setSaved(true); window.setTimeout(() => setSaved(false), 2500) }
  const clearLocalData = () => {
    for (const key of ['synova-last-session', 'synova-settings', 'synova-muse-host', 'synova-muse-token', 'synova-muse-auto']) localStorage.removeItem(key)
    muse.disconnect()
    setMuseHost('')
    setMuseKey('')
  }
  return <div className="page settings-page">
    <header className="page-heading"><div><h1>Settings</h1><p>Adjust Synova for comfort, safety, and your research setup.</p></div><button className="button" onClick={save}>{saved ? 'Settings saved' : 'Save changes'}</button></header>
    <div className="settings-layout">
      <div className="settings-nav" aria-label="Settings sections"><a href="#eeg">EEG headset</a><a href="#classifier">Movement detection</a><a href="#hardware">Hardware</a><a href="#application">Application</a><a href="#data">Data</a></div>
      <div className="settings-content">
        <Panel id="eeg" className="settings-section" title={<div className="settings-title"><div><h2>Muse 2 headset</h2><p>Connect through the Mac companion on the same Wi-Fi</p></div></div>}>
          <div className="setting-row"><div><strong>Headset connection</strong><span>{muse.message}</span></div><strong className={muse.status?.connected ? 'safe-label' : 'muted-label'}>{muse.status?.connected ? 'Live' : muse.enabled && muse.status ? 'Mac found' : muse.enabled ? 'Connecting' : 'Not connected'}</strong></div>
          <div className="muse-steps"><strong>Before connecting</strong><ol><li>On the Mac, open the <b>muse_bridge</b> folder and double-click <b>Setup Synova Muse.command</b> once.</li><li>Turn on Muse 2, then double-click <b>Start Synova Muse.command</b>.</li><li>Enter the Mac address and access key shown in that window below.</li></ol></div>
          <div className="muse-setup"><label>Mac address<input value={museHost} onChange={event => setMuseHost(event.target.value)} placeholder="192.168.1.5:8765" autoCapitalize="none" autoCorrect="off" /></label><label>Access key<input type="password" value={museKey} onChange={event => setMuseKey(event.target.value)} placeholder="Key shown on Mac" autoCapitalize="none" autoCorrect="off" /></label><div className="button-row"><button className="button" disabled={!muse.available || !museHost.trim() || museKey.trim().length < 16 || muse.busy} onClick={() => muse.connect(museHost, museKey)}>{muse.enabled ? 'Reconnect' : 'Connect Muse'}</button>{muse.enabled && <button className="button button--secondary" disabled={muse.busy || Boolean(muse.status?.recording?.active)} onClick={muse.disconnect}>Disconnect</button>}</div><small>{muse.available ? 'After the first connection, Synova reconnects automatically when the app opens. Movement detection remains disabled until a model is validated.' : 'Open the iPhone app to connect to a Mac.'}</small></div>
          {muse.status && <div className="muse-details"><span>Mac companion <strong>v{muse.status.bridge_version || '1'}</strong></span><span>Headset <strong>{muse.status.connected ? 'Streaming' : muse.status.state || 'Waiting'}</strong></span><span>Recording <strong>{muse.status.recording?.active ? `${muse.status.recording.rows.toLocaleString()} samples` : 'Off'}</strong></span></div>}
        </Panel>
        <Panel id="classifier" className="settings-section" title={<div className="settings-title"><div><h2>Movement detection</h2><p>Not yet active</p></div></div>}><div className="setting-row"><div><strong>Manual control only</strong><span>Muse signals can be viewed, but Synova does not classify intentions or move the glove from EEG. That requires recorded training data and safety validation.</span></div></div></Panel>
        <Panel id="hardware" className="settings-section" title={<div className="settings-title"><div><h2>Glove</h2><p>Direct Bluetooth connection to the iPhone</p></div></div>}><div className="setting-row"><div><strong>ESP32-S3 connection</strong><span>{gloveMode === 'demo' ? 'Demo mode · no physical movement' : gloveStatus.message}</span></div><strong className={gloveMode === 'hardware' && gloveStatus.ready ? 'safe-label' : 'muted-label'}>{gloveMode === 'hardware' && gloveStatus.ready ? 'Connected' : 'Locked'}</strong></div><div className="setting-row"><div><strong>Physical safety</strong><span>Use a wired stop switch and bench-test all motion before wearing the glove.</span></div></div></Panel>
        <Panel id="application" className="settings-section" title={<div className="settings-title"><div><h2>Application</h2><p>Comfort and accessibility</p></div></div>}><div className="setting-row"><div><strong>Reduce motion</strong><span>Limit interface movement and transitions</span></div><Toggle checked={settings.reduceMotion} onChange={(v) => update('reduceMotion', v)} label="Reduce motion" /></div><div className="setting-row"><div><strong>Higher contrast</strong><span>Strengthen text and panel boundaries</span></div><Toggle checked={settings.highContrast} onChange={(v) => update('highContrast', v)} label="Higher contrast" /></div></Panel>
        <Panel id="data" className="settings-section" title={<div className="settings-title"><div><h2>Prototype data</h2><p>Local storage for demo sessions</p></div></div>}><div className="setting-row"><div><strong>Data location</strong><span>Preferences, last demo session, and the Mac bridge key are stored on this iPhone.</span></div><button className="button button--secondary" disabled={Boolean(muse.status?.recording?.active)} onClick={clearLocalData}>Clear local data</button></div></Panel>
      </div>
    </div>
  </div>
}
