import type { HandState } from '../types'

function OpenHand() {
  return <>
    <path d="M83 196c-11-19-18-44-18-72V80c0-8 5-14 12-14s12 6 12 14v31-67c0-9 6-16 14-16s14 7 14 16v62-75c0-9 6-16 14-16s14 7 14 16v77-63c0-9 6-15 14-15s14 6 14 15v79l17-22c7-9 18-11 26-5 8 7 9 18 3 27l-37 54c-9 14-14 28-14 45H99c0-11-6-20-16-27Z" />
    <path d="M89 111v36M117 106v41M145 108v39M173 124v27M103 165c15 10 38 11 54 1" />
  </>
}

function ClosedHand() {
  return <>
    <path d="M76 104c0-12 9-21 21-21h71c17 0 31 14 31 31v44c0 24-19 43-43 43h-39c-25 0-45-20-45-45v-32c0-7 6-13 13-13h3l-5-2c-5-1-7-3-7-5Z" />
    <path d="M89 84V70c0-9 7-16 16-16s16 7 16 16v13M121 82V59c0-9 7-16 16-16s16 7 16 16v23M153 84V68c0-9 7-16 16-16s16 7 16 16v25M88 126h92M96 155c19 9 47 9 67 0" />
  </>
}

export function HandVisual({ state }: { state: HandState }) {
  const closed = state === 'CLOSE' || state === 'STOPPED'
  return (
    <div className={`hand-visual hand-visual--${state.toLowerCase()}`}>
      <svg key={closed ? 'closed' : 'open'} viewBox="40 0 200 245" role="img" aria-label={`Commanded hand position: ${state.toLowerCase()}`}>
        <g fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
          {closed ? <ClosedHand /> : <OpenHand />}
        </g>
      </svg>
      <span className="hand-visual__label">Commanded position · No sensor feedback</span>
    </div>
  )
}
