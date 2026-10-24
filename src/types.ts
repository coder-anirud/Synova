export type PageId =
  | 'dashboard'
  | 'signals'
  | 'calibration'
  | 'glove'
  | 'sessions'
  | 'analytics'
  | 'settings'

export type HandState = 'REST' | 'OPEN' | 'CLOSE' | 'STOPPED'

export interface AppSettings {
  confidenceThreshold: number
  sustainedDetection: number
  cooldown: number
  signalThreshold: number
  reduceMotion: boolean
  highContrast: boolean
}
