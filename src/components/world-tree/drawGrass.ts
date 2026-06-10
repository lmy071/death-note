/**
 * Grass rendering system — 双层摇曳草叶
 */
import type { HitArea } from './types'
import { createRng } from './canvasUtils'

// ---- Types ----

export interface GrassBlade {
  x: number
  height: number
  width: number
  hue: number        // HSL hue: 80–140 (green–yellow)
  sat: number        // saturation 40–70
  light: number      // lightness 15–35
  phase: number      // sway phase offset
  swaySpeed: number  // individual sway frequency
  swayAmp: number    // max sway offset in px
}

export interface GrassState {
  blades: GrassBlade[]
  fgCount: number     // foreground blade count (for layer separation)
}

// ---- Init ----

export function initGrass(seed: number, canvasW: number): GrassState {
  const blades: GrassBlade[] = []
  const rng = createRng(seed + 9999)

  // Foreground layer: dense, tall, brighter
  const fgCount = Math.max(80, Math.floor(canvasW / 5))
  for (let i = 0; i < fgCount; i++) {
    blades.push({
      x: (i / fgCount) * canvasW + (rng() - 0.5) * (canvasW / fgCount),
      height: 22 + rng() * 32,
      width: 1.8 + rng() * 2.8,
      hue: 85 + rng() * 55,
      sat: 40 + rng() * 30,
      light: 18 + rng() * 17,
      phase: rng() * Math.PI * 2,
      swaySpeed: 0.6 + rng() * 0.8,
      swayAmp: 2 + rng() * 5,
    })
  }

  // Background layer: sparser, shorter, darker — adds depth
  const bgCount = Math.max(40, Math.floor(canvasW / 10))
  for (let i = 0; i < bgCount; i++) {
    blades.push({
      x: (i / bgCount) * canvasW + (rng() - 0.5) * (canvasW / bgCount),
      height: 10 + rng() * 16,
      width: 1 + rng() * 1.5,
      hue: 90 + rng() * 40,
      sat: 30 + rng() * 20,
      light: 10 + rng() * 10,
      phase: rng() * Math.PI * 2,
      swaySpeed: 0.4 + rng() * 0.5,
      swayAmp: 1 + rng() * 3,
    })
  }

  return { blades, fgCount }
}

// ---- Draw ----

export function drawGrass(
  ctx: CanvasRenderingContext2D,
  state: GrassState,
  groundY: number,
  progress: number,
  time: number,
  mouseX?: number,
  mouseY?: number,
): void {
  const { blades, fgCount } = state

  // Draw background layer first (shorter, darker blades)
  for (let i = fgCount; i < blades.length; i++) {
    drawSingleBlade(ctx, blades[i], groundY - 4, progress, time, true, mouseX, mouseY)
  }
  // Draw foreground layer
  for (let i = 0; i < fgCount; i++) {
    drawSingleBlade(ctx, blades[i], groundY + 2, progress, time, false, mouseX, mouseY)
  }
}

const WIND_RADIUS = 80   // mouse influence radius (px)
const WIND_FORCE = 22    // max extra sway at mouse center (px)

function drawSingleBlade(
  ctx: CanvasRenderingContext2D,
  blade: GrassBlade,
  baseY: number,
  progress: number,
  time: number,
  isBg: boolean,
  mouseX?: number,
  mouseY?: number,
): void {
  const h = blade.height * progress
  if (h < 2) return

  // Natural sway
  let sway = Math.sin(time * blade.swaySpeed + blade.phase) * blade.swayAmp * progress

  // Mouse wind: blades bend away from cursor, strongest at tip
  if (mouseX !== undefined && mouseY !== undefined) {
    const dx = blade.x - mouseX
    const dy = baseY - mouseY
    const dist = Math.hypot(dx, dy)
    if (dist < WIND_RADIUS) {
      const t = 1 - dist / WIND_RADIUS             // 1 at centre → 0 at edge
      const force = t * t * WIND_FORCE              // quadratic fall-off
      const dir = dx > 0 ? 1 : -1                    // push away from mouse
      sway += force * dir * (1 + blade.height / 50)  // taller blades bend more
    }
  }

  // Quadratic bezier: base → control point → tip
  const baseX = blade.x
  const cpX = baseX + sway * 0.5
  const cpY = baseY - h * 0.6
  const tipX = baseX + sway
  const tipY = baseY - h

  ctx.beginPath()
  ctx.moveTo(baseX - blade.width * 0.5, baseY)
  ctx.quadraticCurveTo(cpX - blade.width * 0.3, cpY, tipX, tipY)
  ctx.quadraticCurveTo(cpX + blade.width * 0.3, cpY, baseX + blade.width * 0.5, baseY)
  ctx.closePath()

  // Gradient from dark base to lighter tip
  const grad = ctx.createLinearGradient(baseX, baseY, tipX, tipY)
  const alpha = isBg ? 0.6 : 0.85
  grad.addColorStop(0, `hsla(${blade.hue}, ${blade.sat}%, ${blade.light - 4}%, ${alpha * progress})`)
  grad.addColorStop(0.6, `hsla(${blade.hue}, ${blade.sat + 5}%, ${blade.light}%, ${(alpha - 0.1) * progress})`)
  grad.addColorStop(1, `hsla(${blade.hue + 10}, ${blade.sat + 10}%, ${blade.light + 8}%, ${(alpha - 0.3) * progress})`)
  ctx.fillStyle = grad
  ctx.fill()
}
