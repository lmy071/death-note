/**
 * World Tree rendering system — tree structure, trunk, roots, branches, ground, fireflies
 */
import type { PageInfo, BranchNode, HitArea } from './types'
import type { GrassState } from './drawGrass'
import { createRng, lerpColor, GOLDEN, GOLDEN_DARK, BARK, BARK_DARK } from './canvasUtils'
import { drawGrass } from './drawGrass'
import { drawTeruTeruBozu } from './drawTeruTeruBozu'

// ---- Tree state ----

export interface TreeState {
  data: BranchNode[] | null
  globalBranchIdx: number
}

// ---- Build tree structure ----

export function buildTree(rng: () => number, pages: PageInfo[]): TreeState {
  let globalBranchIdx = 0

  const shuffledPages: PageInfo[] = [...pages]
  for (let i = shuffledPages.length - 1; i > 0; i--) {
    const j = Math.floor(rng() * (i + 1))
    ;[shuffledPages[i], shuffledPages[j]] = [shuffledPages[j], shuffledPages[i]]
  }

  const level1Count: number = 2 + Math.floor(rng() * 4)  // 2-5
  const branches: BranchNode[] = []

  for (let i = 0; i < level1Count; i++) {
    branches.push(buildBranch(rng, 1, i, level1Count, () => globalBranchIdx++))
  }

  // Assign real pages to random leaf positions
  const leaves: BranchNode[] = []
  collectLeaves(branches, leaves)
  const shuffled: BranchNode[] = [...leaves]
  for (let i = shuffled.length - 1; i > 0; i--) {
    const j = Math.floor(rng() * (i + 1))
    ;[shuffled[i], shuffled[j]] = [shuffled[j], shuffled[i]]
  }
  for (let i = 0; i < Math.min(shuffledPages.length, shuffled.length); i++) {
    shuffled[i].page = shuffledPages[i]
  }

  return { data: branches, globalBranchIdx }
}

function buildBranch(
  rng: () => number,
  depth: number,
  index: number,
  siblingCount: number,
  nextId: () => number,
): BranchNode {
  const childCount: number = depth < 3 ? (2 + Math.floor(rng() * 4)) : 0

  const branch: BranchNode = {
    depth,
    index,
    children: [],
    page: null,
    lenRatio: 0.6 + rng() * 0.35,
    angleOffset: 0,
    curveWobble: (rng() - 0.5) * 12,
    curveJitter: (rng() - 0.5) * 6,
    thicknessBase: 0,
    leafSize: 2.5 + rng() * 3,
    branchId: nextId(),
    _maxLen: 0,
  }

  for (let i = 0; i < childCount; i++) {
    branch.children.push(buildBranch(rng, depth + 1, i, childCount, nextId))
  }

  return branch
}

function collectLeaves(branches: BranchNode[], out: BranchNode[]): void {
  for (const b of branches) {
    if (b.children.length === 0) out.push(b)
    else collectLeaves(b.children, out)
  }
}

// ---- Init tree visual params (run once per seed, NOT per frame) ----

export function initTreeVisuals(seed: number, treeState: TreeState, canvasH: number): void {
  const rng = createRng(seed)
  const treeData = treeState.data
  if (!treeData) return

  const l1Count: number = treeData.length
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

// ---- Draw full scene ----

export function drawTreeScene(
  ctx: CanvasRenderingContext2D,
  canvasW: number,
  canvasH: number,
  seed: number,
  treeState: TreeState,
  grassState: GrassState,
  progress: number,
  time: number,
  hitAreas: HitArea[],
): void {
  ctx.clearRect(0, 0, canvasW, canvasH)
  hitAreas.length = 0

  const cx: number = canvasW / 2
  const groundY: number = canvasH * 0.92
  const trunkH: number = canvasH * 0.25
  const decoRng: () => number = createRng(seed + 7777)

  drawGround(ctx, cx, groundY, canvasW, canvasH, grassState, progress, time)

  if (progress > 0.05) drawRoots(ctx, cx, groundY, Math.min(1, progress * 3), decoRng)
  if (progress > 0) drawTrunk(ctx, cx, groundY, trunkH, Math.min(1, progress * 2.5), decoRng)

  if (progress > 0.25 && treeState.data) {
    const branchP: number = Math.min(1, (progress - 0.25) / 0.75)
    const topX: number = cx, topY: number = groundY - trunkH

    for (const b of treeState.data) {
      drawBranch(ctx, topX, topY, b, branchP, time, hitAreas)
    }
  }

  if (progress > 0.8) drawFireflies(ctx, canvasW, canvasH, Math.min(1, (progress - 0.8) * 5), decoRng)
}

// ---- Ground ----

function drawGround(
  ctx: CanvasRenderingContext2D,
  cx: number,
  groundY: number,
  canvasW: number,
  canvasH: number,
  grassState: GrassState,
  progress: number,
  time: number,
): void {
  const grad = ctx.createRadialGradient(cx, groundY + 10, 0, cx, groundY + 10, canvasW * 0.45)
  grad.addColorStop(0, `rgba(212, 160, 23, ${0.08 * progress})`)
  grad.addColorStop(0.5, `rgba(45, 138, 78, ${0.04 * progress})`)
  grad.addColorStop(1, 'rgba(0,0,0,0)')
  ctx.fillStyle = grad
  ctx.fillRect(0, groundY - 20, canvasW, canvasH - groundY + 20)

  // Grass tufts
  if (progress > 0.1) {
    drawGrass(ctx, grassState, groundY, Math.min(1, (progress - 0.1) / 0.5), time)
  }
}

// ---- Roots ----

function drawRoots(ctx: CanvasRenderingContext2D, cx: number, groundY: number, progress: number, rng: () => number): void {
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
    ctx.beginPath()
    ctx.moveTo(cx + r.angle * 8, groundY)
    ctx.quadraticCurveTo(cx + r.angle * 20 + (rng() - 0.5) * 15, groundY + len * 0.3, endX, endY)
    ctx.strokeStyle = BARK_DARK
    ctx.lineWidth = Math.max(1, r.thick * (1 - i * 0.08))
    ctx.lineCap = 'round'
    ctx.stroke()
  }
}

// ---- Trunk ----

function drawTrunk(ctx: CanvasRenderingContext2D, cx: number, groundY: number, trunkH: number, progress: number, rng: () => number): void {
  const h: number = trunkH * progress
  if (h <= 0) return
  const topW: number = 8, botW: number = 22, sway: number = 3

  const grad = ctx.createLinearGradient(cx - botW, groundY, cx + botW, groundY - h)
  grad.addColorStop(0, BARK_DARK)
  grad.addColorStop(0.3, BARK)
  grad.addColorStop(0.7, GOLDEN_DARK)
  grad.addColorStop(1, GOLDEN)

  ctx.beginPath()
  ctx.moveTo(cx - botW, groundY)
  ctx.quadraticCurveTo(cx - botW / 2 + sway, groundY - h * 0.5, cx - topW, groundY - h)
  ctx.lineTo(cx + topW, groundY - h)
  ctx.quadraticCurveTo(cx + botW / 2 + sway, groundY - h * 0.5, cx + botW, groundY)
  ctx.closePath()
  ctx.fillStyle = grad
  ctx.fill()

  // Bark texture
  ctx.strokeStyle = 'rgba(0,0,0,0.12)'
  ctx.lineWidth = 1
  for (let i = 0; i < 5; i++) {
    const y: number = groundY - h * (0.15 + i * 0.17)
    const xOff: number = (rng() - 0.5) * 6
    ctx.beginPath()
    ctx.moveTo(cx + xOff - 4, y)
    ctx.lineTo(cx + xOff + 4, y + 8)
    ctx.stroke()
  }

  // Trunk glow
  const glowGrad = ctx.createRadialGradient(cx, groundY - h * 0.5, 5, cx, groundY - h * 0.5, botW * 3)
  glowGrad.addColorStop(0, `rgba(212, 160, 23, ${0.06 * progress})`)
  glowGrad.addColorStop(1, 'rgba(0,0,0,0)')
  ctx.fillStyle = glowGrad
  ctx.fillRect(cx - botW * 3, groundY - h - botW, botW * 6, h + botW * 2)
}

// ---- Branches (recursive) ----

function drawBranch(
  ctx: CanvasRenderingContext2D,
  sx: number,
  sy: number,
  branch: BranchNode,
  parentProgress: number,
  time: number,
  hitAreas: HitArea[],
): void {
  const startThreshold: number = 0.15 + branch.index * 0.05
  const myProgress: number = Math.min(1, Math.max(0, (parentProgress - startThreshold) / (1 - startThreshold + 0.01)))
  if (myProgress <= 0) return

  const margin = 20
  const len: number = branch._maxLen * myProgress
  const angle: number = branch.angleOffset
  let ex: number = sx + Math.sin(angle) * len
  let ey: number = sy - Math.cos(angle) * len

  // Clamp branch endpoint to canvas bounds with margin
  const cw: number = ctx.canvas.width
  const ch: number = ctx.canvas.height
  if (ex < margin || ex > cw - margin || ey < margin || ey > ch - margin) {
    const dx: number = ex - sx
    const dy: number = ey - sy
    const segLen: number = Math.hypot(dx, dy)
    if (segLen > 1e-6) {
      // Shrink until endpoint fits within the margin box
      let t = 1
      for (let step = 0; step < 8; step++) {
        const tx: number = sx + dx * t
        const ty: number = sy + dy * t
        if (tx >= margin && tx <= cw - margin && ty >= margin && ty <= ch - margin) break
        t *= 0.75
      }
      ex = sx + dx * t
      ey = sy + dy * t
    }
  }

  const thickness: number = Math.max(1, branch.thicknessBase - branch.depth * 1.2)
  const depthRatio: number = Math.min(1, branch.depth / 4)
  const color: string = lerpColor(GOLDEN_DARK, GOLDEN, 1 - depthRatio * 0.5)

  ctx.beginPath()
  ctx.moveTo(sx, sy)
  ctx.quadraticCurveTo(
    (sx + ex) / 2 + branch.curveWobble,
    (sy + ey) / 2 - 8 + branch.curveJitter,
    ex, ey
  )
  ctx.strokeStyle = color
  ctx.lineWidth = thickness
  ctx.lineCap = 'round'
  ctx.stroke()

  // Leaf node → teru teru bozu (晴天娃娃)
  if (branch.children.length === 0) {
    if (myProgress > 0.5) {
      // Ensure the doll (which hangs below the endpoint) doesn't overflow the canvas bottom
      const dollH = branch.leafSize * 9.75 // dollW * (300/200) = leafSize * 6.5 * 1.5
      if (ey + dollH <= ch - margin && ex >= margin && ex <= cw - margin) {
        drawTeruTeruBozu(ctx, ex, ey, branch, myProgress, time, hitAreas)
      }
    }
    return
  }

  // Recurse into children
  if (myProgress > 0.3) {
    for (const child of branch.children) {
      drawBranch(ctx, ex, ey, child, myProgress, time, hitAreas)
    }
  }
}

// ---- Fireflies ----

function drawFireflies(ctx: CanvasRenderingContext2D, canvasW: number, canvasH: number, progress: number, rng: () => number): void {
  const n: number = 15
  for (let i = 0; i < n; i++) {
    const fx: number = canvasW * 0.1 + rng() * canvasW * 0.8
    const fy: number = canvasH * 0.08 + rng() * canvasH * 0.6
    const sz: number = 1.5 + rng() * 2
    const alpha: number = (0.3 + rng() * 0.5) * progress

    ctx.beginPath()
    ctx.arc(fx, fy, sz * 4, 0, Math.PI * 2)
    ctx.fillStyle = `rgba(240, 192, 64, ${alpha * 0.08})`
    ctx.fill()

    ctx.beginPath()
    ctx.arc(fx, fy, sz, 0, Math.PI * 2)
    ctx.fillStyle = `rgba(255, 240, 180, ${alpha})`
    ctx.fill()
  }
}
