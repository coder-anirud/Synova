import { useEffect, useState } from 'react'
import { DemoBadge, Panel, ProgressBar } from '../components/UI'
import type { MuseController } from '../hardware/useMuse'

const steps = [
  { title: 'Check the headset', detail: 'Place the headset comfortably and confirm that all four channels are moving on the Signals page.' },
  { title: 'Resting baseline', detail: 'Relax your hands and sit still while Synova records a labeled baseline.', instruction: 'Rest naturally.' },
  { title: 'Imagine opening', detail: 'Keep your hand still. Focus only on imagining the movement.', instruction: 'Imagine opening your hand.' },
  { title: 'Imagine closing', detail: 'Keep your hand still. Focus only on imagining the movement.', instruction: 'Imagine closing your hand.' },
  { title: 'Review', detail: 'Confirm that your labeled recordings were saved. No model performance is fabricated.' },
]

export function Calibration({ muse }: { muse: MuseController }) {
  const [step, setStep] = useState(0)
  const [running, setRunning] = useState(false)
  const [trialProgress, setTrialProgress] = useState(0)
  useEffect(() => {
    if (!running) return
    const timer = window.setInterval(() => setTrialProgress((p) => {
      if (p >= 100) { setRunning(false); return 100 }
      return p + 2
    }), 200)
    return () => window.clearInterval(timer)
  }, [running])
  const live = Boolean(muse.status?.connected)
  const cancelTrial = () => { setRunning(false); setTrialProgress(0) }
  const next = () => { setStep((value) => Math.min(steps.length - 1, value + 1)); cancelTrial() }
  const current = steps[step]
  return <div className="page calibration-page">
    <header className="page-heading"><div><h1>Guided cue practice</h1><p>Learn the rest, open, and close imagery cues before recording research data on the Mac.</p></div>{!live && <DemoBadge />}</header>
    <div className="calibration-layout">
      <Panel className="step-list-panel" title={<h2>Your progress</h2>}>
        <ol className="step-list">{steps.map((item, index) => <li key={item.title} className={`${index === step ? 'is-current' : ''} ${index < step ? 'is-done' : ''}`}><span>{index + 1}</span><div><strong>{item.title}</strong><small>{index < step ? 'Complete' : index === step ? 'Current step' : 'Up next'}</small></div></li>)}</ol>
      </Panel>
      <Panel className="calibration-workspace">
        <span className="step-count">Step {step + 1} of {steps.length}</span>
        <h2>{current.title}</h2>
        <p>{current.detail}</p>
        {current.instruction && <div className="instruction-card"><span>When you are ready</span><strong>{current.instruction}</strong><small>Stay relaxed and breathe normally.</small></div>}
        {step === 0 && <div className="notice"><strong>{live ? 'Muse 2 is streaming' : 'This is a practice workflow'}</strong><p>{live ? 'You can check the live traces while practicing. For research-quality randomized recordings, stop the companion and run Record Synova Training.command on the Mac.' : 'This screen teaches the cues but does not save EEG. The Mac training recorder saves the real trials.'}</p></div>}
        {step > 0 && step < 4 && <div className="trial-progress"><div><span>{running ? 'Practicing cue…' : trialProgress === 100 ? 'Practice trial complete' : 'Ready to practice'}</span><strong>{trialProgress}%</strong></div><ProgressBar value={trialProgress} /></div>}
        {step === 4 && <div className="empty-result"><strong>Practice workflow complete</strong><p>For real data, quit the display companion and double-click Record Synova Training.command on the Mac. The recorder randomizes cues and saves raw labeled trials without enabling glove movement.</p></div>}
        <div className="button-row">
          {step > 0 && <button className="button button--secondary" onClick={() => { cancelTrial(); setStep(step - 1) }}>Back</button>}
          {step > 0 && step < 4 && trialProgress < 100 && <button className="button" onClick={() => running ? cancelTrial() : setRunning(true)}>{running ? 'Cancel trial' : 'Start 10-second practice'}</button>}
          {(step === 0 || trialProgress === 100) && step < 4 && <button className="button" onClick={next}>Continue</button>}
          {step === 4 && <button className="button button--secondary" onClick={() => { setStep(0); setTrialProgress(0) }}>Start again</button>}
        </div>
      </Panel>
    </div>
  </div>
}
