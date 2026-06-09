<template>
  <canvas
    ref="cvs"
    class="world-tree-canvas"
    @click="onClick"
    @mousemove="onMouseMove"
    @mouseleave="onMouseLeave"
  />
  <div v-if="hoveredBranch" class="branch-tooltip" :style="tooltipStyle">
    <div class="branch-tooltip__name">{{ hoveredBranch.label }}</div>
    <div v-if="hoveredBranch.desc" class="branch-tooltip__desc">{{ hoveredBranch.desc }}</div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import type { PageInfo, BranchNode, HitArea } from './types'

const emit = defineEmits<{
  (e: 'ready'): void
}>()
const router = useRouter()
const cvs = ref<HTMLCanvasElement | null>(null)
const hoveredBranch = ref<HitArea | null>(null)
const tooltipPos = ref<{ x: number; y: number }>({ x: 0, y: 0 })

const tooltipStyle = computed(() => ({
  left: `${tooltipPos.value.x + 14}px`,
  top: `${tooltipPos.value.y - 10}px`,
}))

// ---- Real pages ----
const realPages: PageInfo[] = [
  { label: 'LeetCode 题解', route: '/code/leet-code', desc: '算法题解集' },
  { label: '笔记', route: '/md/md-note', desc: '技术笔记' },
  { label: '粒子特效', route: '/fun/particle-canvas', desc: 'Canvas 粒子动画' },
  { label: '折线图', route: '/fun/line-chart', desc: '数据可视化' },
]

// ---- Tree structure ----
let treeData: BranchNode[] | null = null
let branchHitAreas: HitArea[] = []
let globalBranchIdx: number = 0

// ---- Canvas state ----
let ctx: CanvasRenderingContext2D | null = null
let animId: number | null = null
let canvasW: number = 0, canvasH: number = 0, dpr: number = 1
let growthProgress: number = 0
let currentSeed: number = 0

// Colors
const GOLDEN: string = '#d4a017'
const GOLDEN_DARK: string = '#8b6914'
const BARK: string = '#6b4423'
const BARK_DARK: string = '#3d2510'

let resize = function(): void {
  const el = cvs.value
  if (!el) return
  const rect = el.getBoundingClientRect()
  dpr = window.devicePixelRatio || 1
  canvasW = rect.width
  canvasH = rect.height
  el.width = canvasW * dpr
  el.height = canvasH * dpr
  ctx = el.getContext('2d')
  ctx!.scale(dpr, dpr)
}

// Seeded RNG
function createRng(seed: number): () => number {
  let s: number = seed
  return (): number => {
    s = (s * 16807) % 2147483647
    return (s - 1) / 2147483646
  }
}

function lerpColor(c1: string, c2: string, t: number): string {
  const p = (c: string): [number, number, number] => [parseInt(c.slice(1, 3), 16), parseInt(c.slice(3, 5), 16), parseInt(c.slice(5, 7), 16)]
  const [r1, g1, b1] = p(c1), [r2, g2, b2] = p(c2)
  return `rgb(${Math.round(r1 + (r2 - r1) * t)},${Math.round(g1 + (g2 - g1) * t)},${Math.round(b1 + (b2 - b1) * t)})`
}

// ---- Build 4-level tree structure ----
function buildTree(rng: () => number): BranchNode[] {
  globalBranchIdx = 0

  const pages: PageInfo[] = [...realPages]
  for (let i = pages.length - 1; i > 0; i--) {
    const j = Math.floor(rng() * (i + 1))
    ;[pages[i], pages[j]] = [pages[j], pages[i]]
  }

  const level1Count: number = 2 + Math.floor(rng() * 4)  // 2-5
  const branches: BranchNode[] = []

  for (let i = 0; i < level1Count; i++) {
    branches.push(buildBranch(rng, 1, i, level1Count))
  }

  // Assign real pages to random leaf positions
  const leaves: BranchNode[] = []
  collectLeaves(branches, leaves)
  const shuffled: BranchNode[] = [...leaves]
  for (let i = shuffled.length - 1; i > 0; i--) {
    const j = Math.floor(rng() * (i + 1))
    ;[shuffled[i], shuffled[j]] = [shuffled[j], shuffled[i]]
  }
  for (let i = 0; i < Math.min(pages.length, shuffled.length); i++) {
    shuffled[i].page = pages[i]
  }

  return branches
}

function buildBranch(rng: () => number, depth: number, index: number, siblingCount: number): BranchNode {
  const childCount: number = depth < 3 ? (2 + Math.floor(rng() * 4)) : 0

  const branch: BranchNode = {
    depth,
    index,
    children: [],
    page: null,
    // All random visual params computed once, never changes across frames
    lenRatio: 0.6 + rng() * 0.35,
    angleOffset: 0,           // filled by initTreeVisuals
    curveWobble: (rng() - 0.5) * 12,
    curveJitter: (rng() - 0.5) * 6,
    thicknessBase: 0,         // filled by initTreeVisuals
    leafSize: 2.5 + rng() * 3,
    branchId: globalBranchIdx++,
    _maxLen: 0,               // filled by initTreeVisuals
  }

  for (let i = 0; i < childCount; i++) {
    branch.children.push(buildBranch(rng, depth + 1, i, childCount))
  }

  return branch
}

function collectLeaves(branches: BranchNode[], out: BranchNode[]): void {
  for (const b of branches) {
    if (b.children.length === 0) out.push(b)
    else collectLeaves(b.children, out)
  }
}

// ---- Pre-compute all visual params (run once per seed, NOT per frame) ----
function initTreeVisuals(): void {
  const rng = createRng(currentSeed)
  treeData = buildTree(rng)

  const l1Count: number = treeData.length
  // Spread adapts to branch count: 2 branches = 60°, 5 branches = full 120°
  const totalSpread: number = Math.PI / 3 + (Math.PI / 3) * (l1Count - 2) / 3
  const startAngle: number = -totalSpread / 2

  for (let i = 0; i < l1Count; i++) {
    const b = treeData[i]
    b.angleOffset = startAngle + (i / (l1Count - 1 || 1)) * totalSpread + (rng() - 0.5) * 0.08
    b.thicknessBase = 7 - b.depth * 1.5
    b._maxLen = canvasH * (0.22 + rng() * 0.15)
    initChildVisuals(b, rng)
  }
}

function initChildVisuals(parent: BranchNode, rng: () => number): void {
  const n: number = parent.children.length
  if (n === 0) return

  // Spread wider with more children: 2 children = 40°, 5 children = 80°
  const childSpread: number = Math.PI * (0.22 + 0.08 * n + rng() * 0.06)
  const parentAngle: number = parent.angleOffset || 0

  for (let i = 0; i < n; i++) {
    const child: BranchNode = parent.children[i]
    const offset: number = -childSpread / 2 + (i / (n - 1 || 1)) * childSpread
    const raw: number = parentAngle + offset + (rng() - 0.5) * 0.12
    child.angleOffset = Math.max(-Math.PI / 3, Math.min(Math.PI / 3, raw))
    child.thicknessBase = Math.max(1, (parent.thicknessBase || 5) - 1.5)
    child._maxLen = parent._maxLen * child.lenRatio * 0.92
    initChildVisuals(child, rng)
  }
}

// ---- Draw ----
function drawTree(progress: number, time: number): void {
  if (!ctx) return
  ctx.clearRect(0, 0, canvasW, canvasH)
  branchHitAreas = []

  const cx: number = canvasW / 2
  const groundY: number = canvasH * 0.92
  const trunkH: number = canvasH * 0.25
  const decoRng: () => number = createRng(currentSeed + 7777)  // deterministic for decorations

  drawGround(cx, groundY, progress)

  // Grass is drawn inside drawGround()
  if (progress > 0.05) drawRoots(cx, groundY, Math.min(1, progress * 3), decoRng)
  if (progress > 0) drawTrunk(cx, groundY, trunkH, Math.min(1, progress * 2.5), decoRng)

  if (progress > 0.25 && treeData) {
    const branchP: number = Math.min(1, (progress - 0.25) / 0.75)
    const topX: number = cx, topY: number = groundY - trunkH

    for (const b of treeData) {
      drawBranch(topX, topY, b, branchP, time)
    }
  }

  if (progress > 0.8) drawFireflies(Math.min(1, (progress - 0.8) * 5), decoRng)
}

function drawGround(cx: number, groundY: number, progress: number): void {
  const grad = ctx!.createRadialGradient(cx, groundY + 10, 0, cx, groundY + 10, canvasW * 0.45)
  grad.addColorStop(0, `rgba(212, 160, 23, ${0.08 * progress})`)
  grad.addColorStop(0.5, `rgba(45, 138, 78, ${0.04 * progress})`)
  grad.addColorStop(1, 'rgba(0,0,0,0)')
  ctx!.fillStyle = grad
  ctx!.fillRect(0, groundY - 20, canvasW, canvasH - groundY + 20)

  // Grass tufts at bottom
  if (progress > 0.1) {
    drawGrass(groundY, Math.min(1, (progress - 0.1) / 0.5))
  }
}

// ---- Grass system ----
interface GrassBlade {
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

let grassBlades: GrassBlade[] = []

function initGrass(): void {
  grassBlades = []
  const rng = createRng(currentSeed + 9999)
  // Foreground layer: dense, tall, brighter
  const fgCount = Math.max(80, Math.floor(canvasW / 5))
  for (let i = 0; i < fgCount; i++) {
    grassBlades.push({
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
    grassBlades.push({
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
}

function drawGrass(groundY: number, progress: number): void {
  // Use idleTime when tree is fully grown, otherwise fall back to performance.now
  const time = fullyGrown ? idleTime : performance.now() * 0.001

  // Draw background layer first (shorter, darker blades), then foreground
  // Background blades are stored after foreground blades in the array
  const fgCount = grassBlades.length && grassBlades[0].height > 20
    ? grassBlades.findIndex((b, i) => i > 0 && b.height <= 20)
    : grassBlades.length

  // Draw background layer
  for (let i = fgCount >= 0 ? fgCount : grassBlades.length; i < grassBlades.length; i++) {
    const blade = grassBlades[i]
    drawSingleBlade(blade, groundY - 4, progress, time, true)
  }
  // Draw foreground layer
  for (let i = 0; i < (fgCount >= 0 ? fgCount : grassBlades.length); i++) {
    const blade = grassBlades[i]
    drawSingleBlade(blade, groundY + 2, progress, time, false)
  }
}

function drawSingleBlade(blade: GrassBlade, baseY: number, progress: number, time: number, isBg: boolean): void {
  const h = blade.height * progress
  if (h < 2) return

  // Sway
  const sway = Math.sin(time * blade.swaySpeed + blade.phase) * blade.swayAmp * progress

  // Quadratic bezier: base → control point → tip
  const baseX = blade.x
  const cpX = baseX + sway * 0.5
  const cpY = baseY - h * 0.6
  const tipX = baseX + sway
  const tipY = baseY - h

  ctx!.beginPath()
  ctx!.moveTo(baseX - blade.width * 0.5, baseY)
  ctx!.quadraticCurveTo(cpX - blade.width * 0.3, cpY, tipX, tipY)
  ctx!.quadraticCurveTo(cpX + blade.width * 0.3, cpY, baseX + blade.width * 0.5, baseY)
  ctx!.closePath()

  // Gradient from dark base to lighter tip
  const grad = ctx!.createLinearGradient(baseX, baseY, tipX, tipY)
  const alpha = isBg ? 0.6 : 0.85
  grad.addColorStop(0, `hsla(${blade.hue}, ${blade.sat}%, ${blade.light - 4}%, ${alpha * progress})`)
  grad.addColorStop(0.6, `hsla(${blade.hue}, ${blade.sat + 5}%, ${blade.light}%, ${(alpha - 0.1) * progress})`)
  grad.addColorStop(1, `hsla(${blade.hue + 10}, ${blade.sat + 10}%, ${blade.light + 8}%, ${(alpha - 0.3) * progress})`)
  ctx!.fillStyle = grad
  ctx!.fill()
}


function drawRoots(cx: number, groundY: number, progress: number, rng: () => number): void {
  const roots: { angle: number; len: number; thick: number }[] = [
    { angle: -0.6, len: 80, thick: 4 },
    { angle: -0.3, len: 60, thick: 3 },
    { angle: 0.2, len: 65, thick: 3.5 },
    { angle: 0.5, len: 75, thick: 4 },
    { angle: -0.85, len: 50, thick: 2.5 },
    { angle: 0.75, len: 55, thick: 2.5 },
  ]
  for (let i = 0; i < roots.length; i++) {
    const r = roots[i]
    const p: number = Math.min(1, progress * (1 + i * 0.12))
    if (p <= 0) continue
    const len: number = r.len * p
    const endX: number = cx + Math.cos(Math.PI / 2 + r.angle + (rng() - 0.5) * 0.2) * len
    const endY: number = groundY + Math.abs(Math.sin(Math.PI / 2 + r.angle)) * len * 0.3 + len * 0.5
    ctx!.beginPath()
    ctx!.moveTo(cx + r.angle * 8, groundY)
    ctx!.quadraticCurveTo(cx + r.angle * 20 + (rng() - 0.5) * 15, groundY + len * 0.3, endX, endY)
    ctx!.strokeStyle = BARK_DARK
    ctx!.lineWidth = Math.max(1, r.thick * (1 - i * 0.08))
    ctx!.lineCap = 'round'
    ctx!.stroke()
  }
}

function drawTrunk(cx: number, groundY: number, trunkH: number, progress: number, rng: () => number): void {
  const h: number = trunkH * progress
  if (h <= 0) return
  const topW: number = 8, botW: number = 22, sway: number = 3

  const grad = ctx!.createLinearGradient(cx - botW, groundY, cx + botW, groundY - h)
  grad.addColorStop(0, BARK_DARK)
  grad.addColorStop(0.3, BARK)
  grad.addColorStop(0.7, GOLDEN_DARK)
  grad.addColorStop(1, GOLDEN)

  ctx!.beginPath()
  ctx!.moveTo(cx - botW, groundY)
  ctx!.quadraticCurveTo(cx - botW / 2 + sway, groundY - h * 0.5, cx - topW, groundY - h)
  ctx!.lineTo(cx + topW, groundY - h)
  ctx!.quadraticCurveTo(cx + botW / 2 + sway, groundY - h * 0.5, cx + botW, groundY)
  ctx!.closePath()
  ctx!.fillStyle = grad
  ctx!.fill()

  // Bark texture
  ctx!.strokeStyle = 'rgba(0,0,0,0.12)'
  ctx!.lineWidth = 1
  for (let i = 0; i < 5; i++) {
    const y: number = groundY - h * (0.15 + i * 0.17)
    const xOff: number = (rng() - 0.5) * 6
    ctx!.beginPath()
    ctx!.moveTo(cx + xOff - 4, y)
    ctx!.lineTo(cx + xOff + 4, y + 8)
    ctx!.stroke()
  }

  // Trunk glow
  const glowGrad = ctx!.createRadialGradient(cx, groundY - h * 0.5, 5, cx, groundY - h * 0.5, botW * 3)
  glowGrad.addColorStop(0, `rgba(212, 160, 23, ${0.06 * progress})`)
  glowGrad.addColorStop(1, 'rgba(0,0,0,0)')
  ctx!.fillStyle = glowGrad
  ctx!.fillRect(cx - botW * 3, groundY - h - botW, botW * 6, h + botW * 2)
}

// Recursive branch drawing — NO rng calls, all params pre-computed
function drawBranch(sx: number, sy: number, branch: BranchNode, parentProgress: number, time: number): void {
  const startThreshold: number = 0.15 + branch.index * 0.05
  const myProgress: number = Math.min(1, Math.max(0, (parentProgress - startThreshold) / (1 - startThreshold + 0.01)))
  if (myProgress <= 0) return

  const len: number = branch._maxLen * myProgress
  const angle: number = branch.angleOffset
  const ex: number = sx + Math.sin(angle) * len
  const ey: number = sy - Math.cos(angle) * len

  const thickness: number = Math.max(1, branch.thicknessBase - branch.depth * 1.2)
  const depthRatio: number = Math.min(1, branch.depth / 4)
  const color: string = lerpColor(GOLDEN_DARK, GOLDEN, 1 - depthRatio * 0.5)

  ctx!.beginPath()
  ctx!.moveTo(sx, sy)
  ctx!.quadraticCurveTo(
    (sx + ex) / 2 + branch.curveWobble,
    (sy + ey) / 2 - 8 + branch.curveJitter,
    ex, ey
  )
  ctx!.strokeStyle = color
  ctx!.lineWidth = thickness
  ctx!.lineCap = 'round'
  ctx!.stroke()

  // Leaf (level 4) → teru teru bozu (晴天娃娃)
  if (branch.children.length === 0) {
    if (myProgress > 0.5) drawTeruTeruBozu(ex, ey, branch, myProgress, time)
    return
  }

  // Recurse into children
  if (myProgress > 0.3) {
    for (const child of branch.children) {
      drawBranch(ex, ey, child, myProgress, time)
    }
  }
}

function drawTeruTeruBozu(x: number, y: number, branch: BranchNode, progress: number, time: number): void {
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
  ctx!.beginPath()
  ctx!.moveTo(attachX, attachY)
  ctx!.quadraticCurveTo(
    attachX + swayX * 0.5, attachY + stringLen * 0.5,
    headCX, headCY - headR
  )
  ctx!.strokeStyle = `rgba(200, 180, 140, ${alpha * 0.6})`
  ctx!.lineWidth = 0.8
  ctx!.stroke()

  // ---- Outer glow ----
  const glowFlicker: number = 0.7 + 0.3 * Math.sin(time * 0.4 + branch.branchId)
  ctx!.beginPath()
  ctx!.arc(headCX, headCY, headR * 2.2 * glowFlicker, 0, Math.PI * 2)
  ctx!.fillStyle = hasPage
    ? `rgba(240, 192, 64, ${alpha * glowFlicker * 0.12})`
    : `rgba(180, 210, 255, ${alpha * glowFlicker * 0.06})`
  ctx!.fill()

  // ---- Body (triangular cloth) ----
  ctx!.save()
  ctx!.translate(headCX, headCY + headR * 0.6)
  ctx!.rotate(swayAngle * 0.5)

  const bodyGrad = ctx!.createLinearGradient(0, 0, 0, bodyH)
  bodyGrad.addColorStop(0, `rgba(240, 235, 220, ${alpha * 0.92})`)
  bodyGrad.addColorStop(0.5, `rgba(225, 218, 200, ${alpha * 0.85})`)
  bodyGrad.addColorStop(1, `rgba(210, 200, 180, ${alpha * 0.7})`)

  ctx!.beginPath()
  ctx!.moveTo(-bodyW * 0.5, 0)
  // Left curve
  ctx!.quadraticCurveTo(-bodyW * 0.55, bodyH * 0.5, -bodyW * 0.35, bodyH)
  // Bottom edge
  ctx!.quadraticCurveTo(0, bodyH + sz * 0.4, bodyW * 0.35, bodyH)
  // Right curve
  ctx!.quadraticCurveTo(bodyW * 0.55, bodyH * 0.5, bodyW * 0.5, 0)
  ctx!.closePath()
  ctx!.fillStyle = bodyGrad
  ctx!.fill()

  // Body fold lines
  ctx!.strokeStyle = `rgba(180, 170, 150, ${alpha * 0.2})`
  ctx!.lineWidth = 0.5
  ctx!.beginPath()
  ctx!.moveTo(-bodyW * 0.15, bodyH * 0.3)
  ctx!.quadraticCurveTo(0, bodyH * 0.6, bodyW * 0.1, bodyH * 0.35)
  ctx!.stroke()

  ctx!.restore()

  // ---- Neck tie ----
  ctx!.beginPath()
  const neckY: number = headCY + headR * 0.6
  ctx!.moveTo(headCX - bodyW * 0.5, neckY)
  ctx!.quadraticCurveTo(headCX, neckY + sz * 0.5, headCX + bodyW * 0.5, neckY)
  ctx!.strokeStyle = `rgba(180, 160, 120, ${alpha * 0.7})`
  ctx!.lineWidth = 1.2
  ctx!.stroke()

  // ---- Head (cloth ball) ----
  const headGrad = ctx!.createRadialGradient(
    headCX - headR * 0.25, headCY - headR * 0.25, headR * 0.1,
    headCX, headCY, headR
  )
  headGrad.addColorStop(0, `rgba(255, 252, 245, ${alpha * 0.95})`)
  headGrad.addColorStop(0.6, `rgba(240, 235, 220, ${alpha * 0.9})`)
  headGrad.addColorStop(1, `rgba(215, 205, 185, ${alpha * 0.8})`)

  ctx!.beginPath()
  ctx!.arc(headCX, headCY, headR, 0, Math.PI * 2)
  ctx!.fillStyle = headGrad
  ctx!.fill()

  // Head outline (subtle)
  ctx!.strokeStyle = `rgba(180, 170, 150, ${alpha * 0.25})`
  ctx!.lineWidth = 0.6
  ctx!.stroke()

  // ---- Face ----
  const eyeOffX: number = headR * 0.3
  const eyeY: number = headCY - headR * 0.1
  const eyeR: number = sz * 0.25

  // Eyes — small dots
  ctx!.fillStyle = hasPage
    ? `rgba(60, 40, 20, ${alpha * 0.85})`
    : `rgba(80, 60, 40, ${alpha * 0.6})`

  // Left eye
  ctx!.beginPath()
  ctx!.arc(headCX - eyeOffX, eyeY, eyeR, 0, Math.PI * 2)
  ctx!.fill()

  // Right eye
  ctx!.beginPath()
  ctx!.arc(headCX + eyeOffX, eyeY, eyeR, 0, Math.PI * 2)
  ctx!.fill()

  // Mouth — small curved line
  const mouthY: number = headCY + headR * 0.25
  ctx!.beginPath()
  ctx!.arc(headCX, mouthY - sz * 0.3, sz * 0.4, 0.15 * Math.PI, 0.85 * Math.PI, false)
  ctx!.strokeStyle = hasPage
    ? `rgba(60, 40, 20, ${alpha * 0.7})`
    : `rgba(80, 60, 40, ${alpha * 0.45})`
  ctx!.lineWidth = 0.7
  ctx!.stroke()

  // Cheek blush (for real-page dolls)
  if (hasPage) {
    ctx!.beginPath()
    ctx!.arc(headCX - eyeOffX - sz * 0.1, eyeY + sz * 0.5, sz * 0.3, 0, Math.PI * 2)
    ctx!.fillStyle = `rgba(240, 160, 140, ${alpha * 0.2})`
    ctx!.fill()
    ctx!.beginPath()
    ctx!.arc(headCX + eyeOffX + sz * 0.1, eyeY + sz * 0.5, sz * 0.3, 0, Math.PI * 2)
    ctx!.fillStyle = `rgba(240, 160, 140, ${alpha * 0.2})`
    ctx!.fill()
  }

  // ---- Label — only for real pages ----
  if (hasPage) {
    const labelAlpha: number = alpha * 0.9
    if (labelAlpha > 0.05) {
      ctx!.save()
      ctx!.font = 'bold 11px Avenir, Helvetica, Arial, sans-serif'
      ctx!.textAlign = 'center'
      ctx!.textBaseline = 'bottom'
      ctx!.shadowColor = `rgba(0, 0, 0, ${labelAlpha * 0.8})`
      ctx!.shadowBlur = 4
      ctx!.fillStyle = `rgba(255, 220, 120, ${labelAlpha})`
      ctx!.fillText(branch.page!.label, headCX, headCY - headR - 4)
      ctx!.shadowBlur = 0
      ctx!.restore()
    }
  }

  // ---- Hit area — only for real pages ----
  if (hasPage && progress > 0.7) {
    branchHitAreas.push({
      x: headCX,
      y: headCY,
      radius: Math.max(20, headR * 2),
      label: branch.page!.label,
      desc: branch.page!.desc,
      route: branch.page!.route,
    })
  }
}

function drawFireflies(progress: number, rng: () => number): void {
  const n: number = 15
  for (let i = 0; i < n; i++) {
    const fx: number = canvasW * 0.1 + rng() * canvasW * 0.8
    const fy: number = canvasH * 0.08 + rng() * canvasH * 0.6
    const sz: number = 1.5 + rng() * 2
    const alpha: number = (0.3 + rng() * 0.5) * progress

    ctx!.beginPath()
    ctx!.arc(fx, fy, sz * 4, 0, Math.PI * 2)
    ctx!.fillStyle = `rgba(240, 192, 64, ${alpha * 0.08})`
    ctx!.fill()

    ctx!.beginPath()
    ctx!.arc(fx, fy, sz, 0, Math.PI * 2)
    ctx!.fillStyle = `rgba(255, 240, 180, ${alpha})`
    ctx!.fill()
  }
}

// ---- Animation ----
const GROWTH_MS: number = 4200
let startTime: number | null = null
let fullyGrown: boolean = false

function newSeed(): void {
  currentSeed = Math.floor(Math.random() * 2147483646) + 1
  initTreeVisuals()
  initGrass()
}

function animate(ts: number): void {
  if (!startTime) startTime = ts
  const elapsed: number = ts - startTime
  let t: number = Math.min(1, elapsed / GROWTH_MS)
  growthProgress = 1 - Math.pow(1 - t, 3)
  drawTree(growthProgress, ts * 0.001)
  if (t < 1) {
    animId = requestAnimationFrame(animate)
  } else {
    fullyGrown = true
    emit('ready')
    animId = requestAnimationFrame(idleLoop)
  }
}

let idleTime: number = 0
function idleLoop(ts: number): void {
  idleTime += 0.01
  drawTree(1, idleTime)
  animId = requestAnimationFrame(idleLoop)
}

// ---- Interaction ----
function onClick(e: MouseEvent): void {
  if (!fullyGrown) return
  const rect = cvs.value!.getBoundingClientRect()
  const mx: number = e.clientX - rect.left
  const my: number = e.clientY - rect.top
  for (const a of branchHitAreas) {
    const dx: number = mx - a.x, dy: number = my - a.y
    if (dx * dx + dy * dy <= a.radius * a.radius) {
      router.push(a.route)
      return
    }
  }
}

function onMouseMove(e: MouseEvent): void {
  if (!fullyGrown) return
  const rect = cvs.value!.getBoundingClientRect()
  const mx: number = e.clientX - rect.left
  const my: number = e.clientY - rect.top
  tooltipPos.value = { x: e.clientX, y: e.clientY }

  let found: HitArea | null = null
  for (const a of branchHitAreas) {
    const dx: number = mx - a.x, dy: number = my - a.y
    if (dx * dx + dy * dy <= a.radius * a.radius) { found = a; break }
  }
  hoveredBranch.value = found
  if (cvs.value) cvs.value.style.cursor = found ? 'pointer' : 'default'
}

function onMouseLeave(): void {
  hoveredBranch.value = null
  if (cvs.value) cvs.value.style.cursor = 'default'
}

// Also re-init tree visuals on resize (canvasH changes)
const origResize: () => void = resize
resize = function (): void {
  origResize()
  if (currentSeed) {
    initTreeVisuals()
    initGrass()
  }
}

onMounted(() => {
  newSeed()
  resize()
  window.addEventListener('resize', resize)
  animId = requestAnimationFrame(animate)
})

onUnmounted(() => {
  window.removeEventListener('resize', resize)
  if (animId) cancelAnimationFrame(animId)
})
</script>

<style scoped>
.world-tree-canvas {
  display: block;
  width: 100%;
  height: 100%;
  cursor: default;
}

.branch-tooltip {
  position: fixed;
  pointer-events: none;
  z-index: 100;
  padding: 6px 12px;
  border-radius: 8px;
  background: rgba(10, 16, 32, 0.95);
  border: 1px solid rgba(212, 160, 23, 0.4);
  backdrop-filter: blur(8px);
  text-align: left;
  white-space: nowrap;
}
.branch-tooltip__name {
  font-size: 13px;
  font-weight: 650;
  color: #f0c040;
}
.branch-tooltip__desc {
  font-size: 11px;
  color: rgba(230, 232, 239, 0.65);
  margin-top: 2px;
}
</style>
