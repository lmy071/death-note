/**
 * Shared canvas drawing utilities
 */

/** Seeded pseudo-random number generator (Lehmer LCG) */
export function createRng(seed: number): () => number {
  let s: number = seed
  return (): number => {
    s = (s * 16807) % 2147483647
    return (s - 1) / 2147483646
  }
}

/** Linearly interpolate between two hex colors (#rrggbb) */
export function lerpColor(c1: string, c2: string, t: number): string {
  const p = (c: string): [number, number, number] => [
    parseInt(c.slice(1, 3), 16),
    parseInt(c.slice(3, 5), 16),
    parseInt(c.slice(5, 7), 16),
  ]
  const [r1, g1, b1] = p(c1), [r2, g2, b2] = p(c2)
  return `rgb(${Math.round(r1 + (r2 - r1) * t)},${Math.round(g1 + (g2 - g1) * t)},${Math.round(b1 + (b2 - b1) * t)})`
}

/** Tree color palette */
export const GOLDEN = '#d4a017'
export const GOLDEN_DARK = '#8b6914'
export const BARK = '#6b4423'
export const BARK_DARK = '#3d2510'
