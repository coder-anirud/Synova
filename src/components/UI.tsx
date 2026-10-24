import type { ReactNode } from 'react'

export function Panel({ children, className = '', title, action, id }: { children: ReactNode; className?: string; title?: ReactNode; action?: ReactNode; id?: string }) {
  return (
    <section id={id} className={`panel ${className}`}>
      {title && <header className="panel__header"><div>{title}</div>{action}</header>}
      {children}
    </section>
  )
}

export function DemoBadge() {
  return <span className="demo-badge">Simulated data</span>
}

export function Toggle({ checked, onChange, label }: { checked: boolean; onChange: (checked: boolean) => void; label: string }) {
  return (
    <button type="button" className={`toggle ${checked ? 'is-on' : ''}`} onClick={() => onChange(!checked)} role="switch" aria-checked={checked} aria-label={label}>
      <span />
    </button>
  )
}

export function ProgressBar({ value, tone = 'cyan' }: { value: number; tone?: 'cyan' | 'violet' | 'green' | 'red' }) {
  return <div className={`progress progress--${tone}`} aria-label={`${value}%`}><span style={{ width: `${Math.max(0, Math.min(100, value))}%` }} /></div>
}
