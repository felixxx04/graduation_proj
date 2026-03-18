export type NoiseMechanism = 'laplace' | 'gaussian' | 'geometric'
export type ApplicationStage = 'data' | 'gradient' | 'model'

export type PrivacyConfig = {
  epsilon: number
  delta: number
  sensitivity: number
  noiseMechanism: NoiseMechanism
  applicationStage: ApplicationStage
  /**
   * Total privacy budget for a demo session.
   * This demo treats each inference call as an "operation" consuming ε.
   */
  privacyBudget: number
}

export type PrivacyEventType = 'recommendation_inference' | 'training_epoch'

export type PrivacyLedgerEvent = {
  id: string
  ts: number
  type: PrivacyEventType
  epsilonSpent: number
  deltaSpent?: number
  note?: string
}

export function clampNumber(value: number, min: number, max: number) {
  if (Number.isNaN(value)) return min
  return Math.min(max, Math.max(min, value))
}

function sampleStandardNormal() {
  // Box–Muller transform
  let u = 0
  let v = 0
  while (u === 0) u = Math.random()
  while (v === 0) v = Math.random()
  return Math.sqrt(-2.0 * Math.log(u)) * Math.cos(2.0 * Math.PI * v)
}

function sampleLaplace(scale: number) {
  // Inverse CDF: X = -b * sgn(U) * ln(1 - 2|U|), U~Unif(-0.5,0.5)
  const u = Math.random() - 0.5
  const s = u < 0 ? -1 : 1
  return -scale * s * Math.log(1 - 2 * Math.abs(u))
}

function sampleGeometricLike(scale: number) {
  // Demo-friendly discrete noise: round Laplace to nearest integer.
  return Math.round(sampleLaplace(scale))
}

export function gaussianSigma({
  epsilon,
  delta,
  sensitivity,
}: Pick<PrivacyConfig, 'epsilon' | 'delta' | 'sensitivity'>) {
  const eps = Math.max(1e-6, epsilon)
  const del = Math.min(0.5, Math.max(1e-12, delta))
  // Common DP-SGD style bound: σ >= (Δ * sqrt(2 ln(1.25/δ))) / ε
  return (sensitivity * Math.sqrt(2 * Math.log(1.25 / del))) / eps
}

export function laplaceScale({
  epsilon,
  sensitivity,
}: Pick<PrivacyConfig, 'epsilon' | 'sensitivity'>) {
  const eps = Math.max(1e-6, epsilon)
  return sensitivity / eps
}

export function applyDpNoiseToScore(score: number, config: PrivacyConfig) {
  if (config.epsilon <= 0) return { noisy: score, noise: 0, scale: Infinity }

  if (config.noiseMechanism === 'gaussian') {
    const sigma = gaussianSigma(config)
    const noise = sampleStandardNormal() * sigma
    return { noisy: score + noise, noise, scale: sigma }
  }

  const b = laplaceScale(config)
  const noise =
    config.noiseMechanism === 'geometric' ? sampleGeometricLike(b) : sampleLaplace(b)
  return { noisy: score + noise, noise, scale: b }
}

export function sumEpsilon(events: PrivacyLedgerEvent[]) {
  return events.reduce((acc, e) => acc + (Number.isFinite(e.epsilonSpent) ? e.epsilonSpent : 0), 0)
}

