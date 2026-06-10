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
import type { PageInfo, HitArea } from './types'
import { createRng } from './canvasUtils'
import { buildTree, initTreeVisuals, drawTreeScene, type TreeState } from './drawTree'
import { initGrass, type GrassState } from './drawGrass'
import { initDollAsset } from './drawTeruTeruBozu'

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

// ---- Canvas state ----
let ctx: CanvasRenderingContext2D | null = null
let animId: number | null = null
let canvasW: number = 0, canvasH: number = 0, dpr: number = 1
let growthProgress: number = 0
let currentSeed: number = 0

// ---- Sub-system state ----
let treeState: TreeState = { data: null, globalBranchIdx: 0 }
let grassState: GrassState = { blades: [], fgCount: 0 }
let branchHitAreas: HitArea[] = []

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

// ---- Seed & init ----

function newSeed(): void {
  currentSeed = Math.floor(Math.random() * 2147483646) + 1
  const rng = createRng(currentSeed)
  treeState = buildTree(rng, realPages)
  initTreeVisuals(currentSeed, treeState, canvasH)
  grassState = initGrass(currentSeed, canvasW)
}

// ---- Animation ----
const GROWTH_MS: number = 4200
let startTime: number | null = null
let fullyGrown: boolean = false
let idleTime: number = 0

function animate(ts: number): void {
  if (!startTime) startTime = ts
  const elapsed: number = ts - startTime
  let t: number = Math.min(1, elapsed / GROWTH_MS)
  growthProgress = 1 - Math.pow(1 - t, 3)
  drawTreeScene(ctx!, canvasW, canvasH, currentSeed, treeState, grassState, growthProgress, ts * 0.001, branchHitAreas)
  if (t < 1) {
    animId = requestAnimationFrame(animate)
  } else {
    fullyGrown = true
    emit('ready')
    animId = requestAnimationFrame(idleLoop)
  }
}

function idleLoop(ts: number): void {
  idleTime += 0.01
  drawTreeScene(ctx!, canvasW, canvasH, currentSeed, treeState, grassState, 1, idleTime, branchHitAreas)
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

// Re-init on resize
const origResize: () => void = resize
resize = function (): void {
  origResize()
  if (currentSeed) {
    initTreeVisuals(currentSeed, treeState, canvasH)
    grassState = initGrass(currentSeed, canvasW)
  }
}

onMounted(() => {
  initDollAsset()
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
