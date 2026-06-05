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

// ---- Collect all pages as branches ----
const viewGlob = import.meta.glob('../../views/**/*.vue', { eager: true })
const leetCodeGlob = import.meta.glob('../../leetCode/*.js', { eager: true })
const mdGlob = import.meta.glob('../../md/**/*.md', { eager: true })

function baseName(p) {
  const idx = p.lastIndexOf('/')
  return idx >= 0 ? p.slice(idx + 1) : p
}

function extractLeadingNumber(name) {
  const m = String(name).match(/^\s*(\d+)\s*\./)
  return m ? Number(m[1]) : Number.POSITIVE_INFINITY
}

const branches = computed(() => {
  const list = []

  // Main pages
  const mainPages = [
    { label: 'LeetCode 题解', route: '/code/leet-code', desc: '算法题解集', group: 'main', icon: '📖' },
    { label: '笔记', route: '/md/md-note', desc: '技术笔记', group: 'main', icon: '📝' },
    { label: '粒子特效', route: '/fun/particle-canvas', desc: 'Canvas 粒子动画', group: 'main', icon: '✨' },
    { label: '折线图', route: '/fun/line-chart', desc: '数据可视化', group: 'main', icon: '📈' },
  ]
  list.push(...mainPages)

  // LeetCode problems
  const problems = Object.keys(leetCodeGlob)
    .map(k => {
      const name = baseName(k).replace(/\.js$/, '')
      const num = extractLeadingNumber(name)
      return { label: name, route: '/code/leet-code', desc: `LeetCode #${num}`, group: 'leetcode', order: num, icon: '🧩' }
    })
    .sort((a, b) => a.order - b.order)
  list.push(...problems)

  // MD directories & notes
  const mdDirs = new Set()
  const notes = Object.keys(mdGlob).map(k => {
    const parts = k.split('/')
    const mdIdx = parts.indexOf('md')
    const dir = mdIdx >= 0 && parts[mdIdx + 1] ? parts[mdIdx + 1] : '未分类'
    mdDirs.add(dir)
    const name = baseName(k).replace(/\.md$/, '')
    return { label: name, route: '/md/md-note', desc: dir, group: 'md', order: 1, icon: '📋' }
  })
  for (const dir of mdDirs) {
    list.push({ label: dir, route: '/md/md-note', desc: '笔记分类', group: 'md-dir', order: 0, icon: '📁' })
  }
  list.push(...notes)

  return list
})

// ---- Tree drawing engine ----
let ctx = null
let animId = null
let canvasW = 0, canvasH = 0, dpr = 1
let growthProgress = 0
let branchHitAreas = []

// Colors
const GOLDEN = '#d4a017'
const GOLDEN_LIGHT = '#f0c040'
const GOLDEN_DARK = '#8b6914'
const GREEN_LEAF = '#2d8a4e'
const GREEN_LIGHT = '#4cbb6c'
const GREEN_DARK = '#1a6b35'
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

// Deterministic seeded RNG
function createRng(seed) {
  let s = seed
  return () => {
    s = (s * 16807) % 2147483647
    return (s - 1) / 2147483646
  }
}

function lerpColor(c1, c2, t) {
  const parse = c => [parseInt(c.slice(1, 3), 16), parseInt(c.slice(3, 5), 16), parseInt(c.slice(5, 7), 16)]
  const [r1, g1, b1] = parse(c1)
  const [r2, g2, b2] = parse(c2)
  const r = Math.round(r1 + (r2 - r1) * t), g = Math.round(g1 + (g2 - g1) * t), b = Math.round(b1 + (b2 - b1) * t)
  return `rgb(${r},${g},${b})`
}

// ============ DRAW ============

function drawTree(progress, time) {
  if (!ctx) return
  ctx.clearRect(0, 0, canvasW, canvasH)
  branchHitAreas = []

  const cx = canvasW / 2
  const groundY = canvasH * 0.92
  const trunkH = canvasH * 0.28
  const rng = createRng(42)

  // Ground glow
  drawGround(cx, groundY, progress)

  // Roots
  if (progress > 0.05) {
    drawRoots(cx, groundY, Math.min(1, progress * 3), rng)
  }

  // Trunk
  if (progress > 0) {
    drawTrunk(cx, groundY, trunkH, Math.min(1, progress * 2.5), rng)
  }

  // Canopy
  if (progress > 0.3) {
    const canopyP = Math.min(1, (progress - 0.3) / 0.7)
    drawCanopy(cx, groundY - trunkH, canopyP, rng, time)
  }
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

function drawCanopy(cx, baseY, progress, rng, time) {
  const allBranches = branches.value
  const leetCodePages = allBranches.filter(b => b.group === 'leetcode')
  const mdDirPages = allBranches.filter(b => b.group === 'md-dir')
  const mdPages = allBranches.filter(b => b.group === 'md')
  const mainPages = allBranches.filter(b => b.group === 'main')
  const funPages = mainPages.filter(p => p.route.startsWith('/fun'))
  const otherPages = mainPages.filter(p => !p.route.startsWith('/fun'))

  // 4 main thick branches (category limbs)
  const H = canvasH
  const categories = [
    { label: '题解', angle: -0.65, len: H * 0.22, thick: 7, children: [] },
    { label: '笔记', angle: -0.15, len: H * 0.25, thick: 6, children: [] },
    { label: '趣味', angle: 0.35, len: H * 0.20, thick: 5, children: [] },
    { label: '更多', angle: 0.70, len: H * 0.18, thick: 5, children: [] },
  ]

  // ---- LeetCode → 题解 ----
  const leetCat = categories[0]
  const leetN = leetCodePages.length
  for (let i = 0; i < leetN; i++) {
    leetCat.children.push({
      ...leetCodePages[i],
      vAngle: -1.3 + (i / Math.max(1, leetN - 1)) * 1.5,
      vLen: H * (0.12 + rng() * 0.14),
      vThick: 1.2 + rng() * 1.0,
    })
  }

  // ---- MD dirs + notes → 笔记 ----
  const mdCat = categories[1]
  let di = 0
  for (const dir of mdDirPages) {
    mdCat.children.push({
      ...dir,
      vAngle: -0.55 + (di / Math.max(1, mdDirPages.length)) * 0.7,
      vLen: H * (0.09 + rng() * 0.07),
      vThick: 2 + rng(),
      isSubCategory: true,
    })
    di++
  }
  for (const note of mdPages) {
    mdCat.children.push({
      ...note,
      vAngle: -0.4 + rng() * 0.6,
      vLen: H * (0.07 + rng() * 0.12),
      vThick: 1 + rng() * 0.8,
    })
  }

  // ---- Fun → 趣味 ----
  const funCat = categories[2]
  for (let i = 0; i < funPages.length; i++) {
    funCat.children.push({
      ...funPages[i],
      vAngle: -0.35 + (i / Math.max(1, funPages.length - 1)) * 0.7,
      vLen: H * (0.10 + rng() * 0.10),
      vThick: 2 + rng() * 0.5,
    })
  }

  // ---- Other → 更多 ----
  const otherCat = categories[3]
  for (let i = 0; i < otherPages.length; i++) {
    otherCat.children.push({
      ...otherPages[i],
      vAngle: -0.3 + (i / Math.max(1, otherPages.length - 1)) * 0.6,
      vLen: H * (0.08 + rng() * 0.08),
      vThick: 1.5 + rng(),
    })
  }

  // Count real branches (categories + children)
  const realCount = categories.length + categories.reduce((s, c) => s + c.children.length, 0)
  // Add decorative branches to guarantee ≥ 50 visual branches
  const minDeco = Math.max(0, 55 - realCount)

  // ---- Draw thick category limbs ----
  for (let ci = 0; ci < categories.length; ci++) {
    const cat = categories[ci]
    const catP = Math.min(1, progress * 2.2 - ci * 0.12)
    if (catP <= 0) continue

    const a = cat.angle
    const len = cat.len * catP
    const endX = cx + Math.sin(a) * len
    const endY = baseY - Math.cos(a) * len

    // Thick branch gradient
    const grad = ctx.createLinearGradient(cx, baseY, endX, endY)
    grad.addColorStop(0, GOLDEN_DARK)
    grad.addColorStop(0.5, GOLDEN)
    grad.addColorStop(1, GREEN_DARK)

    ctx.beginPath()
    ctx.moveTo(cx, baseY)
    ctx.quadraticCurveTo(
      cx + Math.sin(a) * len * 0.5 + (rng() - 0.5) * 10,
      baseY - Math.cos(a) * len * 0.5 - 10,
      endX, endY
    )
    ctx.strokeStyle = grad
    ctx.lineWidth = cat.thick
    ctx.lineCap = 'round'
    ctx.stroke()

    // Flickering glow at main branch endpoint
    if (catP > 0.5) {
      // Each branch has independent flicker phase
      const flickerPhase = time * (1.8 + ci * 0.7) + ci * 2.3
      const flicker = 0.4 + 0.6 * (0.5 + 0.5 * Math.sin(flickerPhase) * Math.cos(flickerPhase * 0.7))
      const baseAlpha = (catP - 0.5) * 2
      const glowAlpha = baseAlpha * 0.35 * flicker

      // Outer glow
      const gGrad = ctx.createRadialGradient(endX, endY, 2, endX, endY, 35)
      gGrad.addColorStop(0, `rgba(240, 192, 64, ${glowAlpha})`)
      gGrad.addColorStop(0.5, `rgba(212, 160, 23, ${glowAlpha * 0.3})`)
      gGrad.addColorStop(1, 'rgba(0,0,0,0)')
      ctx.fillStyle = gGrad
      ctx.fillRect(endX - 35, endY - 35, 70, 70)

      // Title text with flicker
      if (baseAlpha > 0.5) {
        const textAlpha = baseAlpha * flicker * 0.95
        ctx.save()
        ctx.font = 'bold 13px Avenir, Helvetica, Arial, sans-serif'
        ctx.textAlign = 'center'
        ctx.textBaseline = 'bottom'
        // Text shadow/glow
        ctx.shadowColor = `rgba(240, 192, 64, ${textAlpha * 0.6})`
        ctx.shadowBlur = 12
        ctx.fillStyle = `rgba(240, 210, 100, ${textAlpha})`
        ctx.fillText(cat.label, endX, endY - 10)
        ctx.shadowBlur = 0
        ctx.restore()
      }
    }

    // Draw child sub-branches
    for (let bi = 0; bi < cat.children.length; bi++) {
      const child = cat.children[bi]
      const bP = Math.min(1, (catP - 0.25) * 2.8 - bi * 0.008)
      if (bP <= 0) continue
      drawSubBranch(endX, endY, child, bP, rng)
    }
  }

  // ---- Decorative leaf clusters ----
  if (progress > 0.5) {
    drawLeafClusters(cx, baseY, categories, Math.min(1, (progress - 0.5) * 2), rng)
  }

  // ---- Extra decorative branches ----
  if (minDeco > 0 && progress > 0.6) {
    drawDecoBranches(cx, baseY, categories, minDeco, Math.min(1, (progress - 0.6) * 2.5), rng)
  }

  // ---- Floating pollen / firefly particles ----
  if (progress > 0.8) {
    drawFireflies(Math.min(1, (progress - 0.8) * 5), rng)
  }
}

function drawSubBranch(sx, sy, branch, progress, rng) {
  const len = branch.vLen * progress
  const a = branch.vAngle
  const ex = sx + Math.sin(a) * len
  const ey = sy - Math.cos(a) * len

  // Color: golden → green gradient along branch
  const color = progress > 0.5
    ? lerpColor(GOLDEN, GREEN_LEAF, (progress - 0.5) * 2)
    : GOLDEN

  ctx.beginPath()
  ctx.moveTo(sx, sy)
  ctx.quadraticCurveTo(
    (sx + ex) / 2 + (rng() - 0.5) * 8,
    (sy + ey) / 2 + (rng() - 0.5) * 6,
    ex, ey
  )
  ctx.strokeStyle = color
  ctx.lineWidth = branch.vThick
  ctx.lineCap = 'round'
  ctx.stroke()

  // Leaf / fruit at tip
  if (progress > 0.7) {
    const alpha = (progress - 0.7) / 0.3
    const sz = 2.5 + rng() * 3

    // Golden glow
    ctx.beginPath()
    ctx.arc(ex, ey, sz * 2.2, 0, Math.PI * 2)
    ctx.fillStyle = `rgba(212, 160, 23, ${alpha * 0.12})`
    ctx.fill()

    // Leaf dot
    ctx.beginPath()
    ctx.arc(ex, ey, sz, 0, Math.PI * 2)
    ctx.fillStyle = branch.isSubCategory
      ? `rgba(76, 187, 108, ${alpha * 0.85})`
      : `rgba(240, 192, 64, ${alpha * 0.9})`
    ctx.fill()

    // Hit area
    if (progress > 0.85) {
      branchHitAreas.push({
        x: ex, y: ey, radius: Math.max(12, sz * 2.5),
        label: branch.label, desc: branch.desc, route: branch.route,
      })
    }
  }
}

function drawLeafClusters(cx, baseY, categories, progress, rng) {
  for (const cat of categories) {
    const a = cat.angle
    const len = cat.len
    const bx = cx + Math.sin(a) * len
    const by = baseY - Math.cos(a) * len
    const n = 10 + Math.floor(rng() * 8)
    for (let i = 0; i < n; i++) {
      const oa = rng() * Math.PI * 2
      const od = 12 + rng() * 40
      const lx = bx + Math.cos(oa) * od * progress
      const ly = by + Math.sin(oa) * od * progress - 5
      const sz = 2 + rng() * 4
      const isG = rng() > 0.3
      ctx.beginPath()
      ctx.arc(lx, ly, sz, 0, Math.PI * 2)
      ctx.fillStyle = isG
        ? `rgba(76, 187, 108, ${0.3 * progress})`
        : `rgba(240, 192, 64, ${0.25 * progress})`
      ctx.fill()
    }
  }
}

function drawDecoBranches(cx, baseY, categories, count, progress, rng) {
  for (let i = 0; i < count; i++) {
    let sx, sy, ba
    if (rng() < 0.35) {
      // From trunk
      sy = baseY + canvasH * 0.28 - rng() * canvasH * 0.18
      sx = cx + (rng() - 0.5) * 12
      ba = (rng() - 0.5) * 1.4
    } else {
      // From a random category limb
      const cat = categories[Math.floor(rng() * categories.length)]
      const a = cat.angle
      const len = cat.len * rng() * 0.75
      sx = cx + Math.sin(a) * len
      sy = baseY - Math.cos(a) * len
      ba = a + (rng() - 0.5) * 1.0
    }
    const bLen = (18 + rng() * 30) * progress
    const ex = sx + Math.sin(ba) * bLen
    const ey = sy - Math.cos(ba) * bLen

    ctx.beginPath()
    ctx.moveTo(sx, sy)
    ctx.lineTo(ex, ey)
    ctx.strokeStyle = `rgba(212, 160, 23, ${0.25 + rng() * 0.35})`
    ctx.lineWidth = 0.8 + rng() * 1.2
    ctx.lineCap = 'round'
    ctx.stroke()

    // Tiny leaf
    if (progress > 0.4) {
      const sz = 1.5 + rng() * 2.5
      const isG = rng() > 0.35
      ctx.beginPath()
      ctx.arc(ex, ey, sz, 0, Math.PI * 2)
      ctx.fillStyle = isG
        ? `rgba(76, 187, 108, ${0.4 * progress})`
        : `rgba(240, 192, 64, ${0.35 * progress})`
      ctx.fill()
    }
  }
}

function drawFireflies(progress, rng) {
  const n = 12
  for (let i = 0; i < n; i++) {
    const fx = canvasW * 0.15 + rng() * canvasW * 0.7
    const fy = canvasH * 0.1 + rng() * canvasH * 0.55
    const sz = 1.5 + rng() * 2
    const alpha = (0.3 + rng() * 0.5) * progress

    // Outer glow
    ctx.beginPath()
    ctx.arc(fx, fy, sz * 4, 0, Math.PI * 2)
    ctx.fillStyle = `rgba(240, 192, 64, ${alpha * 0.08})`
    ctx.fill()

    // Core
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

function animate(ts) {
  if (!startTime) startTime = ts
  const elapsed = ts - startTime
  let t = Math.min(1, elapsed / GROWTH_MS)
  // Ease-out cubic
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

// Idle: subtle sway + firefly shimmer
let idleTime = 0
function idleLoop(ts) {
  idleTime += 0.01
  // Redraw with slight animated shimmer on fireflies
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

onMounted(() => {
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
