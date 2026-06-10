/**
 * Teru Teru Bozu (晴天娃娃) rendering — anime-style image sprite + spirit rings (魂环)
 *
 * Now uses a high-quality anime SVG asset loaded via Image() for the doll body,
 * with dynamic spirit rings rendered behind as Canvas overlay.
 */
import type { BranchNode, HitArea } from './types'
import { createRng } from './canvasUtils'

// ---- Image asset ----
let dollImg: HTMLImageElement | null = null
let dollImgLoaded = false

/** Call once during init to load the doll sprite. Returns true if already loaded. */
export function initDollAsset(): boolean {
  if (dollImgLoaded) return true
  if (!dollImg) {
    dollImg = new Image()
    dollImg.src = '/assets/teru-teru-bozu.svg'
    dollImg.onload = () => { dollImgLoaded = true }
    dollImg.onerror = () => console.warn('[WorldTree] Failed to load doll asset')
  }
  return dollImgLoaded
}

// ---- Spirit Ring colors (斗罗大陆魂环等级色) ----
const SPIRIT_RING_COLORS = [
  { r: 220, g: 220, b: 240, name: '白环' },
  { r: 255, g: 215, b: 50,  name: '黄环' },
  { r: 180, g: 100, b: 255, name: '紫环' },
  { r: 50,  g: 50,  b: 70,  name: '黑环' },
  { r: 255, g: 50,  b: 50,  name: '红环' },
  { r: 255, g: 140, b: 0,   name: '橙环' },
]

interface SpiritRing {
  colorIdx: number
  radius: number
  speed: number
  tilt: number
  phase: number
  yOffset: number
}

function getSpiritRings(branchId: number, sz: number): SpiritRing[] {
  const rng = createRng(branchId * 37 + 42)
  const count = 1 + Math.floor(rng() * 4)
  const rings: SpiritRing[] = []
  for (let i = 0; i < count; i++) {
    rings.push({
      colorIdx: Math.floor(rng() * SPIRIT_RING_COLORS.length),
      radius: 2.8 + rng() * 1.5,
      speed: 0.4 + rng() * 0.6,
      tilt: 0.5 + rng() * 0.4,
      phase: rng() * Math.PI * 2,
      yOffset: -0.3 + rng() * 0.6,
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
  const tilt = ring.tilt

  const ringCX = cx
  const ringCY = cy + sz * ring.yOffset
  const semiMajor = r
  const semiMinor = r * Math.cos(tilt)
  const pulse = 0.7 + 0.3 * Math.sin(time * 1.5 + ring.phase)

  ctx.save()
  ctx.translate(ringCX, ringCY)
  ctx.rotate(rotation * 0.1)

  // Outer glow
  ctx.beginPath()
  ctx.ellipse(0, 0, semiMajor + 3, semiMinor + 2, 0, 0, Math.PI * 2)
  ctx.strokeStyle = `rgba(${color.r}, ${color.g}, ${color.b}, ${alpha * 0.15 * pulse})`
  ctx.lineWidth = 6
  ctx.stroke()

  // Main ring
  ctx.beginPath()
  ctx.ellipse(0, 0, semiMajor, semiMinor, 0, 0, Math.PI * 2)
  ctx.strokeStyle = `rgba(${color.r}, ${color.g}, ${color.b}, ${alpha * (0.5 + 0.3 * pulse)})`
  ctx.lineWidth = 2
  ctx.stroke()

  // Inner bright edge
  ctx.beginPath()
  ctx.ellipse(0, 0, semiMajor, semiMinor, 0, 0, Math.PI * 2)
  ctx.strokeStyle = `rgba(${Math.min(255, color.r + 80)}, ${Math.min(255, color.g + 80)}, ${Math.min(255, color.b + 80)}, ${alpha * 0.4 * pulse})`
  ctx.lineWidth = 1
  ctx.stroke()

  // Energy particles
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

// ---- SVG natural dimensions (viewBox 0 0 200 300) ----
const DOLL_NATURAL_W = 200
const DOLL_NATURAL_H = 300

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

  const hasPage: boolean = !!branch.page

  // ---- Sway animation ----
  const swayFreq: number = 0.8 + (branch.branchId % 5) * 0.15
  const swayPhase: number = branch.branchId * 2.3
  const swayAngle: number = Math.sin(time * swayFreq + swayPhase) * 0.12
  const swayX: number = Math.sin(time * swayFreq + swayPhase) * 3

  // ---- Scale ----
  // Target head diameter = sz * 3.6 (head in SVG is r=52, viewBox w=200 → head occupies ~52% of width)
  // So total doll width ≈ sz * 3.6 / 0.52 ≈ sz * 6.9, we use a comfortable multiplier
  const dollW = branch.leafSize * 6.5
  const dollH = dollW * (DOLL_NATURAL_H / DOLL_NATURAL_W) // maintain aspect ratio

  // Doll anchor: top-center = attachment point on branch
  const dollCX = x + swayX
  const dollCY = y

  // Head center (for spirit rings / hit area targeting)
  // In SVG: head center is at (100, 118) in 200×300 → relative to dollW/dollH
  const headRelX = 100 / DOLL_NATURAL_W
  const headRelY = 118 / DOLL_NATURAL_H
  const headCX = dollCX
  const headCY = dollCY + dollH * headRelY

  // ---- Background soft glow (awakened dolls only) ----
  if (hasPage) {
    const glowFlicker = 0.7 + 0.3 * Math.sin(time * 0.4 + branch.branchId)
    // Large twin rings behind the doll
    for (let i = 0; i < 2; i++) {
      const ringR = dollW * (0.55 + i * 0.15)
      const ringAlpha = alpha * 0.06 * glowFlicker * (1 - i * 0.3)
      ctx.beginPath()
      ctx.arc(headCX, headCY, ringR, 0, Math.PI * 2)
      ctx.fillStyle = `rgba(255, 200, 100, ${ringAlpha})`
      ctx.fill()
    }
  }

  // ---- Spirit rings (魂环) — behind doll, only for dolls with pages ----
  if (hasPage && alpha > 0.2) {
    const rings = getSpiritRings(branch.branchId, dollW / 6.5)
    for (const ring of rings) {
      drawSpiritRing(ctx, headCX, headCY, ring, dollW / 6.5, alpha * 0.8, time)
    }
  }

  // ---- Awakened doll extra spark overlay (before image) ----
  if (hasPage && alpha > 0.3) {
    const sparkAlpha = alpha * 0.08 * (0.7 + 0.3 * Math.sin(time * 2.0 + branch.branchId))
    ctx.beginPath()
    ctx.arc(headCX, headCY, dollW * 0.6, 0, Math.PI * 2)
    ctx.fillStyle = `rgba(255, 220, 120, ${sparkAlpha})`
    ctx.fill()
  }

  // ---- Draw doll image ----
  ctx.save()
  ctx.globalAlpha = alpha
  ctx.translate(dollCX, dollCY)
  ctx.rotate(swayAngle * 0.3)

  if (dollImg && dollImgLoaded) {
    // Draw image centered at translation origin (top-center anchor)
    ctx.drawImage(dollImg, -dollW / 2, 0, dollW, dollH)

    // Awakened dolls: subtle brightness overlay
    if (hasPage && alpha > 0.4) {
      ctx.globalCompositeOperation = 'overlay'
      ctx.globalAlpha = 0.1 * (alpha - 0.4) / 0.6
      ctx.fillStyle = '#FFE0A0'
      ctx.fillRect(-dollW / 2, 0, dollW, dollH)
      ctx.globalCompositeOperation = 'source-over'
      ctx.globalAlpha = 1
    }
  } else {
    // Fallback: simple silhouette while image loads (skirt shape)
    ctx.fillStyle = `rgba(240, 235, 220, ${alpha * 0.6})`
    ctx.beginPath()
    ctx.arc(0, dollH * headRelY, dollW * 0.28, 0, Math.PI * 2)
    ctx.fill()
    // Upper body
    ctx.beginPath()
    ctx.rect(-dollW * 0.08, dollH * 0.58, dollW * 0.16, dollH * 0.08)
    ctx.fillStyle = `rgba(220, 210, 190, ${alpha * 0.5})`
    ctx.fill()
    // Skirt trapezoid
    ctx.beginPath()
    ctx.moveTo(-dollW * 0.1, dollH * 0.66)
    ctx.lineTo(dollW * 0.1, dollH * 0.66)
    ctx.lineTo(dollW * 0.22, dollH * 0.96)
    ctx.quadraticCurveTo(0, dollH * 1.02, -dollW * 0.22, dollH * 0.96)
    ctx.closePath()
    ctx.fillStyle = `rgba(200, 190, 170, ${alpha * 0.45})`
    ctx.fill()
  }

  ctx.restore()

  // ---- Label — only for real pages ----
  if (hasPage) {
    const labelAlpha: number = alpha * 0.9
    if (labelAlpha > 0.05) {
      ctx.save()
      ctx.font = 'bold 10px "M PLUS 1p", "Noto Sans SC", Avenir, Helvetica, sans-serif'
      ctx.textAlign = 'center'
      ctx.textBaseline = 'bottom'
      ctx.shadowColor = `rgba(0, 0, 0, ${labelAlpha * 0.7})`
      ctx.shadowBlur = 3
      ctx.fillStyle = `rgba(255, 220, 120, ${labelAlpha})`
      ctx.fillText(branch.page!.label, headCX, dollCY - 6)
      ctx.shadowBlur = 0
      ctx.restore()
    }
  }

  // ---- Hit area — only for real pages ----
  if (hasPage && progress > 0.7) {
    hitAreas.push({
      x: headCX,
      y: headCY,
      radius: Math.max(24, dollW * 0.5),
      label: branch.page!.label,
      desc: branch.page!.desc,
      route: branch.page!.route,
    })
  }
}
