export function Brand({ compact = false }: { compact?: boolean }) {
  return (
    <div className={`brand ${compact ? 'brand--compact' : ''}`} aria-label="Synova — Where Thought Becomes Motion">
      <div className="brand__copy">
        <span className="brand__name">SYNOVA</span>
        {!compact && <span className="brand__tagline">Where Thought Becomes Motion.</span>}
      </div>
    </div>
  )
}
