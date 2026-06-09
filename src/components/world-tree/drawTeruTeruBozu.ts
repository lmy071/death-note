/**
 * Teru Teru Bozu (晴天娃娃) rendering — hanging cloth dolls with spirit rings (魂环)
 */
import type { BranchNode, HitArea } from './types'
import { createRng } from './canvasUtils'

// ---- Spirit Ring colors (斗罗大陆魂环等级色) ----
const SPIRIT_RING_COLORS = [
  { r: 220, g: 220, b: 240, name: '白环' },   // 十年 — 白色
  { r: 255, g: 215, b: 50,  name: '黄环' },   // 百年 — 黄色
  { r: 180, g: 100, b: 255, name: '紫环' },   // 千年 — 紫色
  { r: 50,  g: 50,  b: 70,  name: '黑环' },   // 万年 — 黑色
  { r: 255, g: 50,  b: 50,  name: '红环' },   // 十万年 — 红色
  { r: 255, g: 140, b: 0,   name: '橙环' },   // 神 — 金橙色
]

interface SpiritRing {
  colorIdx: number
  radius: number   // ring radius (in sz units)
  speed: number    // rotation speed
  tilt: number     // tilt angle for 3D perspective (0 = face-on, π/2 = edge-on)
  phase: number    // initial rotation phase
  yOffset: number  // vertical offset from head center
}

// Deterministic ring assignment per branch
function getSpiritRings(branchId: number, sz: number): SpiritRing[] {
  const rng = createRng(branchId * 37 + 42)
  const count = 1 + Math.floor(rng() * 4)  // 1-4 rings
  const rings: SpiritRing[] = []
  for (let i = 0; i < count; i++) {
    rings.push({
      colorIdx: Math.floor(rng() * SPIRIT_RING_COLORS.length),
      radius: 2.8 + rng() * 1.5,   // varies per ring
      speed: 0.4 + rng() * 0.6,     // rotation speed
      tilt: 0.5 + rng() * 0.4,      // perspective tilt
      phase: rng() * Math.PI * 2,
      yOffset: -0.3 + rng() * 0.6,  // slight vertical scatter
    })
  }
  return rings
}

// ---- Draw spirit ring (3D rotated ellipse with glow) ----
function drawSpiritRing(
  ctx: CanvasRenderingContext2D,
  cx: number,
  cy: number,
  ring: SpiritRing,
  sz: number,
  alpha: number,
  time: number,
): void {
  const color = SPIRIT_RING_COLORS[ring.colorIdx]
  const r = sz * ring.radius
  const rotation = time * ring.speed + ring.phase
  const tilt = ring.tilt  // how much the ring is tilted toward viewer

  // The ring center
  const ringCX = cx
  const ringCY = cy + sz * ring.yOffset

  // Ellipse params: semi-major = r, semi-minor = r * cos(tilt)
  const semiMajor = r
  const semiMinor = r * Math.cos(tilt)

  // Pulsating glow intensity
  const pulse = 0.7 + 0.3 * Math.sin(time * 1.5 + ring.phase)

  ctx.save()
  ctx.translate(ringCX, ringCY)
  ctx.rotate(rotation * 0.1)  // slow overall rotation

  // ---- Outer glow ----
  ctx.beginPath()
  ctx.ellipse(0, 0, semiMajor + 3, semiMinor + 2, 0, 0, Math.PI * 2)
  ctx.strokeStyle = `rgba(${color.r}, ${color.g}, ${color.b}, ${alpha * 0.15 * pulse})`
  ctx.lineWidth = 6
  ctx.stroke()

  // ---- Main ring ----
  ctx.beginPath()
  ctx.ellipse(0, 0, semiMajor, semiMinor, 0, 0, Math.PI * 2)
  const ringAlpha = alpha * (0.5 + 0.3 * pulse)
  ctx.strokeStyle = `rgba(${color.r}, ${color.g}, ${color.b}, ${ringAlpha})`
  ctx.lineWidth = 2
  ctx.stroke()

  // ---- Inner bright edge ----
  ctx.beginPath()
  ctx.ellipse(0, 0, semiMajor, semiMinor, 0, 0, Math.PI * 2)
  ctx.strokeStyle = `rgba(${Math.min(255, color.r + 80)}, ${Math.min(255, color.g + 80)}, ${Math.min(255, color.b + 80)}, ${alpha * 0.4 * pulse})`
  ctx.lineWidth = 1
  ctx.stroke()

  // ---- Energy particles along ring ----
  const particleCount = 6
  for (let i = 0; i < particleCount; i++) {
    const angle = rotation + (i / particleCount) * Math.PI * 2
    const px = Math.cos(angle) * semiMajor
    const py = Math.sin(angle) * semiMinor
    const particleAlpha = alpha * 0.6 * pulse * (0.5 + 0.5 * Math.sin(angle + time * 2))
    if (particleAlpha < 0.05) continue

    ctx.beginPath()
    ctx.arc(px, py, 1.5 + pulse, 0, Math.PI * 2)
    ctx.fillStyle = `rgba(${Math.min(255, color.r + 100)}, ${Math.min(255, color.g + 100)}, ${Math.min(255, color.b + 100)}, ${particleAlpha})`
    ctx.fill()
  }

  ctx.restore()
}

// ---- Draw ----

export function drawTeruTeruBozu(
  ctx: CanvasRenderingContext2D,
  x: number,
  y: number,
  branch: BranchNode,
  progress: number,
  time: number,
  hitAreas: HitArea[],
): void {
  const alpha: number = (progress - 0.5) / 0.5
  if (alpha < 0.05) return

  const sz: number = branch.leafSize * 1.2  // base scale unit
  const hasPage: boolean = !!branch.page

  // ---- Sway animation ----
  const swayFreq: number = 0.8 + (branch.branchId % 5) * 0.15
  const swayPhase: number = branch.branchId * 2.3
  const swayAngle: number = Math.sin(time * swayFreq + swayPhase) * 0.12
  const swayX: number = Math.sin(time * swayFreq + swayPhase) * 3

  // ---- Geometry ----
  const stringLen: number = sz * 3.5
  const headR: number = sz * 1.8
  const bodyW: number = sz * 2.8
  const bodyH: number = sz * 3.5

  // Attachment point (branch tip)
  const attachX: number = x
  const attachY: number = y

  // Head center (below string)
  const headCX: number = attachX + swayX
  const headCY: number = attachY + stringLen + headR

  // ---- Draw string ----
  ctx.beginPath()
  ctx.moveTo(attachX, attachY)
  ctx.quadraticCurveTo(
    attachX + swayX * 0.5, attachY + stringLen * 0.5,
    headCX, headCY - headR
  )
  ctx.strokeStyle = `rgba(200, 180, 140, ${alpha * 0.6})`
  ctx.lineWidth = 0.8
  ctx.stroke()

  // ---- Outer glow ----
  const glowFlicker: number = 0.7 + 0.3 * Math.sin(time * 0.4 + branch.branchId)
  ctx.beginPath()
  ctx.arc(headCX, headCY, headR * 2.2 * glowFlicker, 0, Math.PI * 2)
  ctx.fillStyle = hasPage
    ? `rgba(240, 192, 64, ${alpha * glowFlicker * 0.12})`
    : `rgba(180, 210, 255, ${alpha * glowFlicker * 0.06})`
  ctx.fill()

  // ---- Spirit rings (魂环) — only for dolls with pages ----
  if (hasPage && alpha > 0.2) {
    const rings = getSpiritRings(branch.branchId, sz)
    for (const ring of rings) {
      drawSpiritRing(ctx, headCX, headCY, ring, sz, alpha * 0.8, time)
    }
  }

  // ---- Body (triangular cloth) ----
  ctx.save()
  ctx.translate(headCX, headCY + headR * 0.6)
  ctx.rotate(swayAngle * 0.5)

  const bodyGrad = ctx.createLinearGradient(0, 0, 0, bodyH)
  bodyGrad.addColorStop(0, `rgba(240, 235, 220, ${alpha * 0.92})`)
  bodyGrad.addColorStop(0.5, `rgba(225, 218, 200, ${alpha * 0.85})`)
  bodyGrad.addColorStop(1, `rgba(210, 200, 180, ${alpha * 0.7})`)

  ctx.beginPath()
  ctx.moveTo(-bodyW * 0.5, 0)
  // Left curve
  ctx.quadraticCurveTo(-bodyW * 0.55, bodyH * 0.5, -bodyW * 0.35, bodyH)
  // Bottom edge
  ctx.quadraticCurveTo(0, bodyH + sz * 0.4, bodyW * 0.35, bodyH)
  // Right curve
  ctx.quadraticCurveTo(bodyW * 0.55, bodyH * 0.5, bodyW * 0.5, 0)
  ctx.closePath()
  ctx.fillStyle = bodyGrad
  ctx.fill()

  // Body fold lines
  ctx.strokeStyle = `rgba(180, 170, 150, ${alpha * 0.2})`
  ctx.lineWidth = 0.5
  ctx.beginPath()
  ctx.moveTo(-bodyW * 0.15, bodyH * 0.3)
  ctx.quadraticCurveTo(0, bodyH * 0.6, bodyW * 0.1, bodyH * 0.35)
  ctx.stroke()

  ctx.restore()

  // ---- Neck tie ----
  ctx.beginPath()
  const neckY: number = headCY + headR * 0.6
  ctx.moveTo(headCX - bodyW * 0.5, neckY)
  ctx.quadraticCurveTo(headCX, neckY + sz * 0.5, headCX + bodyW * 0.5, neckY)
  ctx.strokeStyle = `rgba(180, 160, 120, ${alpha * 0.7})`
  ctx.lineWidth = 1.2
  ctx.stroke()

  // ---- Head (cloth ball) ----
  const headGrad = ctx.createRadialGradient(
    headCX - headR * 0.25, headCY - headR * 0.25, headR * 0.1,
    headCX, headCY, headR
  )
  headGrad.addColorStop(0, `rgba(255, 252, 245, ${alpha * 0.95})`)
  headGrad.addColorStop(0.6, `rgba(240, 235, 220, ${alpha * 0.9})`)
  headGrad.addColorStop(1, `rgba(215, 205, 185, ${alpha * 0.8})`)

  ctx.beginPath()
  ctx.arc(headCX, headCY, headR, 0, Math.PI * 2)
  ctx.fillStyle = headGrad
  ctx.fill()

  // Head outline (subtle)
  ctx.strokeStyle = `rgba(180, 170, 150, ${alpha * 0.25})`
  ctx.lineWidth = 0.6
  ctx.stroke()

  // ---- Face ----
  const eyeOffX: number = headR * 0.3
  const eyeY: number = headCY - headR * 0.1
  const eyeR: number = sz * 0.25

  // Eyes — small dots
  ctx.fillStyle = hasPage
    ? `rgba(60, 40, 20, ${alpha * 0.85})`
    : `rgba(80, 60, 40, ${alpha * 0.6})`

  // Left eye
  ctx.beginPath()
  ctx.arc(headCX - eyeOffX, eyeY, eyeR, 0, Math.PI * 2)
  ctx.fill()

  // Right eye
  ctx.beginPath()
  ctx.arc(headCX + eyeOffX, eyeY, eyeR, 0, Math.PI * 2)
  ctx.fill()

  // Mouth — small curved line
  const mouthY: number = headCY + headR * 0.25
  ctx.beginPath()
  ctx.arc(headCX, mouthY - sz * 0.3, sz * 0.4, 0.15 * Math.PI, 0.85 * Math.PI, false)
  ctx.strokeStyle = hasPage
    ? `rgba(60, 40, 20, ${alpha * 0.7})`
    : `rgba(80, 60, 40, ${alpha * 0.45})`
  ctx.lineWidth = 0.7
  ctx.stroke()

  // Cheek blush (for real-page dolls)
  if (hasPage) {
    ctx.beginPath()
    ctx.arc(headCX - eyeOffX - sz * 0.1, eyeY + sz * 0.5, sz * 0.3, 0, Math.PI * 2)
    ctx.fillStyle = `rgba(240, 160, 140, ${alpha * 0.2})`
    ctx.fill()
    ctx.beginPath()
    ctx.arc(headCX + eyeOffX + sz * 0.1, eyeY + sz * 0.5, sz * 0.3, 0, Math.PI * 2)
    ctx.fillStyle = `rgba(240, 160, 140, ${alpha * 0.2})`
    ctx.fill()
  }

  // ---- Label — only for real pages ----
  if (hasPage) {
    const labelAlpha: number = alpha * 0.9
    if (labelAlpha > 0.05) {
      ctx.save()
      ctx.font = 'bold 11px Avenir, Helvetica, Arial, sans-serif'
      ctx.textAlign = 'center'
      ctx.textBaseline = 'bottom'
      ctx.shadowColor = `rgba(0, 0, 0, ${labelAlpha * 0.8})`
      ctx.shadowBlur = 4
      ctx.fillStyle = `rgba(255, 220, 120, ${labelAlpha})`
      ctx.fillText(branch.page!.label, headCX, headCY - headR - 4)
      ctx.shadowBlur = 0
      ctx.restore()
    }
  }

  // ---- Hit area — only for real pages ----
  if (hasPage && progress > 0.7) {
    hitAreas.push({
      x: headCX,
      y: headCY,
      radius: Math.max(20, headR * 2),
      label: branch.page!.label,
      desc: branch.page!.desc,
      route: branch.page!.route,
    })
  }
}
