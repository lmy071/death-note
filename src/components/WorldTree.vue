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

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'

const emit = defineEmits(['ready'])
const router = useRouter()
const cvs = ref(null)
const hoveredBranch = ref(null)
const tooltipPos = ref({ x: 0, y: 0 })

const tooltipStyle = computed(() => ({
  left: `${tooltipPos.value.x + 14}px`,
  top: `${tooltipPos.value.y - 10}px`,
}))

// ---- Real pages ----
const realPages = [
  { label: 'LeetCode 题解', route: '/code/leet-code', desc: '算法题解集' },
  { label: '笔记', route: '/md/md-note', desc: '技术笔记' },
  { label: '粒子特效', route: '/fun/particle-canvas', desc: 'Canvas 粒子动画' },
  { label: '折线图', route: '/fun/line-chart', desc: '数据可视化' },
]

// ---- Tree structure ----
let treeData = null
let branchHitAreas = []
let globalBranchIdx = 0

// ---- Canvas state ----
let ctx = null
let animId = null
let canvasW = 0, canvasH = 0, dpr = 1
let growthProgress = 0
let currentSeed = 0

// Colors
const GOLDEN = '#d4a017'
const GOLDEN_DARK = '#8b6914'
const BARK = '#6b4423'
const BARK_DARK = '#3d2510'

function resize() {
  const el = cvs.value
  if (!el) return
  const rect = el.getBoundingClientRect()
  dpr = window.devicePixelRatio || 1
  canvasW = rect.width
  canvasH = rect.height
  el.width = canvasW * dpr
  el.height = canvasH * dpr
  ctx = el.getContext('2d')
  ctx.scale(dpr, dpr)
}

// Seeded RNG
function createRng(seed) {
  let s = seed
  return () => {
    s = (s * 16807) % 2147483647
    return (s - 1) / 2147483646
  }
}

function lerpColor(c1, c2, t) {
  const p = c => [parseInt(c.slice(1, 3), 16), parseInt(c.slice(3, 5), 16), parseInt(c.slice(5, 7), 16)]
  const [r1, g1, b1] = p(c1), [r2, g2, b2] = p(c2)
  return `rgb(${Math.round(r1 + (r2 - r1) * t)},${Math.round(g1 + (g2 - g1) * t)},${Math.round(b1 + (b2 - b1) * t)})`
}

// ---- Build 4-level tree structure ----
function buildTree(rng) {
  globalBranchIdx = 0

  const pages = [...realPages]
  for (let i = pages.length - 1; i > 0; i--) {
    const j = Math.floor(rng() * (i + 1))
    ;[pages[i], pages[j]] = [pages[j], pages[i]]
  }

  const level1Count = 2 + Math.floor(rng() * 4)  // 2-5
  const branches = []

  for (let i = 0; i < level1Count; i++) {
    branches.push(buildBranch(rng, 1, i, level1Count))
  }

  // Assign real pages to random leaf positions
  const leaves = []
  collectLeaves(branches, leaves)
  const shuffled = [...leaves]
  for (let i = shuffled.length - 1; i > 0; i--) {
    const j = Math.floor(rng() * (i + 1))
    ;[shuffled[i], shuffled[j]] = [shuffled[j], shuffled[i]]
  }
  for (let i = 0; i < Math.min(pages.length, shuffled.length); i++) {
    shuffled[i].page = pages[i]
  }

  return branches
}

function buildBranch(rng, depth, index, siblingCount) {
  const childCount = depth < 3 ? (2 + Math.floor(rng() * 4)) : 0

  const branch = {
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

function collectLeaves(branches, out) {
  for (const b of branches) {
    if (b.children.length === 0) out.push(b)
    else collectLeaves(b.children, out)
  }
}

// ---- Pre-compute all visual params (run once per seed, NOT per frame) ----
function initTreeVisuals() {
  const rng = createRng(currentSeed)
  treeData = buildTree(rng)

  const l1Count = treeData.length
  // Spread adapts to branch count: 2 branches = 60°, 5 branches = full 120°
  const totalSpread = Math.PI / 3 + (Math.PI / 3) * (l1Count - 2) / 3
  const startAngle = -totalSpread / 2

  for (let i = 0; i < l1Count; i++) {
    const b = treeData[i]
    b.angleOffset = startAngle + (i / (l1Count - 1 || 1)) * totalSpread + (rng() - 0.5) * 0.08
    b.thicknessBase = 7 - b.depth * 1.5
    b._maxLen = canvasH * (0.22 + rng() * 0.15)
    initChildVisuals(b, rng)
  }
}

function initChildVisuals(parent, rng) {
  const n = parent.children.length
  if (n === 0) return

  // Spread wider with more children: 2 children = 40°, 5 children = 80°
  const childSpread = Math.PI * (0.22 + 0.08 * n + rng() * 0.06)
  const parentAngle = parent.angleOffset || 0

  for (let i = 0; i < n; i++) {
    const child = parent.children[i]
    const offset = -childSpread / 2 + (i / (n - 1 || 1)) * childSpread
    const raw = parentAngle + offset + (rng() - 0.5) * 0.12
    child.angleOffset = Math.max(-Math.PI / 3, Math.min(Math.PI / 3, raw))
    child.thicknessBase = Math.max(1, (parent.thicknessBase || 5) - 1.5)
    child._maxLen = parent._maxLen * child.lenRatio * 0.92
    initChildVisuals(child, rng)
  }
}

// ---- Draw ----
function drawTree(progress, time) {
  if (!ctx) return
  ctx.clearRect(0, 0, canvasW, canvasH)
  branchHitAreas = []

  const cx = canvasW / 2
  const groundY = canvasH * 0.92
  const trunkH = canvasH * 0.25
  const decoRng = createRng(currentSeed + 7777)  // deterministic for decorations

  drawGround(cx, groundY, progress)

  if (progress > 0.05) drawRoots(cx, groundY, Math.min(1, progress * 3), decoRng)
  if (progress > 0) drawTrunk(cx, groundY, trunkH, Math.min(1, progress * 2.5), decoRng)

  if (progress > 0.25 && treeData) {
    const branchP = Math.min(1, (progress - 0.25) / 0.75)
    const topX = cx, topY = groundY - trunkH

    for (const b of treeData) {
      drawBranch(topX, topY, b, branchP, time)
    }
  }

  if (progress > 0.8) drawFireflies(Math.min(1, (progress - 0.8) * 5), decoRng)
}

function drawGround(cx, groundY, progress) {
  const grad = ctx.createRadialGradient(cx, groundY + 10, 0, cx, groundY + 10, canvasW * 0.45)
  grad.addColorStop(0, `rgba(212, 160, 23, ${0.08 * progress})`)
  grad.addColorStop(0.5, `rgba(45, 138, 78, ${0.04 * progress})`)
  grad.addColorStop(1, 'rgba(0,0,0,0)')
  ctx.fillStyle = grad
  ctx.fillRect(0, groundY - 20, canvasW, canvasH - groundY + 20)
}

function drawRoots(cx, groundY, progress, rng) {
  const roots = [
    { angle: -0.6, len: 80, thick: 4 },
    { angle: -0.3, len: 60, thick: 3 },
    { angle: 0.2, len: 65, thick: 3.5 },
    { angle: 0.5, len: 75, thick: 4 },
    { angle: -0.85, len: 50, thick: 2.5 },
    { angle: 0.75, len: 55, thick: 2.5 },
  ]
  for (let i = 0; i < roots.length; i++) {
    const r = roots[i]
    const p = Math.min(1, progress * (1 + i * 0.12))
    if (p <= 0) continue
    const len = r.len * p
    const endX = cx + Math.cos(Math.PI / 2 + r.angle + (rng() - 0.5) * 0.2) * len
    const endY = groundY + Math.abs(Math.sin(Math.PI / 2 + r.angle)) * len * 0.3 + len * 0.5
    ctx.beginPath()
    ctx.moveTo(cx + r.angle * 8, groundY)
    ctx.quadraticCurveTo(cx + r.angle * 20 + (rng() - 0.5) * 15, groundY + len * 0.3, endX, endY)
    ctx.strokeStyle = BARK_DARK
    ctx.lineWidth = Math.max(1, r.thick * (1 - i * 0.08))
    ctx.lineCap = 'round'
    ctx.stroke()
  }
}

function drawTrunk(cx, groundY, trunkH, progress, rng) {
  const h = trunkH * progress
  if (h <= 0) return
  const topW = 8, botW = 22, sway = 3

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
    const y = groundY - h * (0.15 + i * 0.17)
    const xOff = (rng() - 0.5) * 6
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

// Recursive branch drawing — NO rng calls, all params pre-computed
function drawBranch(sx, sy, branch, parentProgress, time) {
  const startThreshold = 0.15 + branch.index * 0.05
  const myProgress = Math.min(1, Math.max(0, (parentProgress - startThreshold) / (1 - startThreshold + 0.01)))
  if (myProgress <= 0) return

  const len = branch._maxLen * myProgress
  const angle = branch.angleOffset
  const ex = sx + Math.sin(angle) * len
  const ey = sy - Math.cos(angle) * len

  const thickness = Math.max(1, branch.thicknessBase - branch.depth * 1.2)
  const depthRatio = Math.min(1, branch.depth / 4)
  const color = lerpColor(GOLDEN_DARK, GOLDEN, 1 - depthRatio * 0.5)

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

  // Leaf (level 4) → fruit
  if (branch.children.length === 0) {
    if (myProgress > 0.5) drawFruit(ex, ey, branch, myProgress, time)
    return
  }

  // Recurse into children
  if (myProgress > 0.3) {
    for (const child of branch.children) {
      drawBranch(ex, ey, child, myProgress, time)
    }
  }
}

function drawFruit(x, y, branch, progress, time) {
  const alpha = (progress - 0.5) / 0.5
  const sz = branch.leafSize
  const hasPage = !!branch.page

  // Slow flicker
  const flickerSpeed = 0.2 + (branch.branchId % 7) * 0.07
  const flickerPhase = time * flickerSpeed + branch.branchId * 1.7
  const flicker = 0.2 + 0.8 * (0.5 + 0.5 * Math.sin(flickerPhase))

  // Outer glow
  ctx.beginPath()
  ctx.arc(x, y, sz * 3 * flicker, 0, Math.PI * 2)
  ctx.fillStyle = hasPage
    ? `rgba(240, 192, 64, ${alpha * flicker * 0.22})`
    : `rgba(76, 187, 108, ${alpha * flicker * 0.15})`
  ctx.fill()

  // Fruit
  ctx.beginPath()
  ctx.arc(x, y, sz * flicker, 0, Math.PI * 2)
  ctx.fillStyle = hasPage
    ? `rgba(240, 192, 64, ${alpha * flicker * 0.95})`
    : `rgba(76, 187, 108, ${alpha * flicker * 0.75})`
  ctx.fill()

  // Highlight
  ctx.beginPath()
  ctx.arc(x - sz * 0.2, y - sz * 0.2, sz * 0.35 * flicker, 0, Math.PI * 2)
  ctx.fillStyle = `rgba(255, 255, 220, ${alpha * flicker * 0.25})`
  ctx.fill()

  // Label — only for real pages, slow fade
  if (hasPage && flicker > 0.4) {
    const textAlpha = alpha * (flicker - 0.4) / 0.6 * 0.95
    if (textAlpha > 0.05) {
      ctx.save()
      ctx.font = 'bold 12px Avenir, Helvetica, Arial, sans-serif'
      ctx.textAlign = 'center'
      ctx.textBaseline = 'bottom'
      ctx.shadowColor = `rgba(0, 0, 0, ${textAlpha * 0.8})`
      ctx.shadowBlur = 4
      ctx.fillStyle = `rgba(255, 220, 120, ${textAlpha})`
      ctx.fillText(branch.page.label, x, y - sz - 5)
      ctx.shadowBlur = 0
      ctx.restore()
    }
  }

  // Hit area — only for real pages
  if (hasPage && progress > 0.7) {
    branchHitAreas.push({
      x, y,
      radius: Math.max(16, sz * 3),
      label: branch.page.label,
      desc: branch.page.desc,
      route: branch.page.route,
    })
  }
}

function drawFireflies(progress, rng) {
  const n = 15
  for (let i = 0; i < n; i++) {
    const fx = canvasW * 0.1 + rng() * canvasW * 0.8
    const fy = canvasH * 0.08 + rng() * canvasH * 0.6
    const sz = 1.5 + rng() * 2
    const alpha = (0.3 + rng() * 0.5) * progress

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

// ---- Animation ----
const GROWTH_MS = 4200
let startTime = null
let fullyGrown = false

function newSeed() {
  currentSeed = Math.floor(Math.random() * 2147483646) + 1
  initTreeVisuals()
}

function animate(ts) {
  if (!startTime) startTime = ts
  const elapsed = ts - startTime
  let t = Math.min(1, elapsed / GROWTH_MS)
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

let idleTime = 0
function idleLoop(ts) {
  idleTime += 0.01
  drawTree(1, idleTime)
  animId = requestAnimationFrame(idleLoop)
}

// ---- Interaction ----
function onClick(e) {
  if (!fullyGrown) return
  const rect = cvs.value.getBoundingClientRect()
  const mx = e.clientX - rect.left
  const my = e.clientY - rect.top
  for (const a of branchHitAreas) {
    const dx = mx - a.x, dy = my - a.y
    if (dx * dx + dy * dy <= a.radius * a.radius) {
      router.push(a.route)
      return
    }
  }
}

function onMouseMove(e) {
  if (!fullyGrown) return
  const rect = cvs.value.getBoundingClientRect()
  const mx = e.clientX - rect.left
  const my = e.clientY - rect.top
  tooltipPos.value = { x: e.clientX, y: e.clientY }

  let found = null
  for (const a of branchHitAreas) {
    const dx = mx - a.x, dy = my - a.y
    if (dx * dx + dy * dy <= a.radius * a.radius) { found = a; break }
  }
  hoveredBranch.value = found
  if (cvs.value) cvs.value.style.cursor = found ? 'pointer' : 'default'
}

function onMouseLeave() {
  hoveredBranch.value = null
  if (cvs.value) cvs.value.style.cursor = 'default'
}

// Also re-init tree visuals on resize (canvasH changes)
const origResize = resize
resize = function () {
  origResize()
  if (currentSeed) initTreeVisuals()
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
