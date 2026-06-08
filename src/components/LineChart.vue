<template>
  <div ref="wrap" class="line-chart-wrap">
    <canvas ref="cvs" @mousemove="onMove" @mouseleave="onLeave"></canvas>
    <!-- Tooltip -->
    <div
      v-if="tooltip.visible"
      class="chart-tooltip"
      :style="{ left: tooltip.x + 'px', top: tooltip.y + 'px' }"
    >
      <div class="tooltip-title">{{ tooltip.title }}</div>
      <div
        v-for="item in tooltip.items"
        :key="item.name"
        class="tooltip-row"
      >
        <span class="tooltip-dot" :style="{ background: item.color }"></span>
        <span class="tooltip-name">{{ item.name }}</span>
        <span class="tooltip-value">{{ item.value }}</span>
      </div>
    </div>
    <!-- Legend -->
    <div v-if="options.legend !== false && series.length" class="chart-legend">
      <span
        v-for="(s, i) in series"
        :key="i"
        class="legend-item"
        @click="toggleSeries(i)"
      >
        <span class="legend-dot" :style="{ background: s._color }"></span>
        <span :class="{ 'legend-name': true, dimmed: s._hidden }">{{ s.name || `系列${i + 1}` }}</span>
      </span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted, onUnmounted, watch } from 'vue'

// ---- Types ----
interface ChartSeries {
  name?: string
  data: number[]
  color?: string
  smooth?: boolean
  area?: boolean
  lineWidth?: number
  areaOpacity?: number
  _color: string
  _hidden: boolean
  _smooth: boolean
  _area: boolean
  _lineWidth: number
  _areaOpacity: number
}

interface TooltipItem {
  name: string
  color: string
  value: number
}

interface TooltipState {
  visible: boolean
  x: number
  y: number
  title: string
  items: TooltipItem[]
}

interface Point {
  x: number
  y: number
  value: number
}

interface ChartOptions {
  xAxis?: { data?: string[] }
  yAxis?: {
    min?: number
    max?: number
    splitNumber?: number
    formatter?: (v: number) => string
  }
  series?: Array<{
    name?: string
    data: number[]
    color?: string
    smooth?: boolean
    area?: boolean
    lineWidth?: number
    areaOpacity?: number
  }>
  legend?: boolean
}

// ---- Props ----
const props = defineProps<{
  options: ChartOptions
  height?: number
}>()

const cvs = ref<HTMLCanvasElement | null>(null)
const wrap = ref<HTMLDivElement | null>(null)
let ctx: CanvasRenderingContext2D | null = null
let w = 0
let h = 0
let dpr = 1
let animId: number | null = null
let animProgress = 0
let animStart = 0
const ANIM_DURATION = 800

// Padding for chart area
const PAD = { top: 20, right: 20, bottom: 40, left: 50 }

// Tooltip state
const tooltip = reactive<TooltipState>({ visible: false, x: 0, y: 0, title: '', items: [] })

// Color palette
const palette = [
  '#82b1ff', '#ff80ab', '#69f0ae', '#ffd740', '#b388ff',
  '#84ffff', '#ff6e40', '#40c4ff', '#ea80fc', '#b2ff59'
]

const series = computed<ChartSeries[]>(() => {
  const raw = props.options.series || []
  return raw.map((s, i) => ({
    ...s,
    _color: s.color || palette[i % palette.length],
    _hidden: false,
    _smooth: s.smooth !== false,
    _area: s.area || false,
    _lineWidth: s.lineWidth || 2,
    _areaOpacity: s.areaOpacity || 0.15
  }))
})

const xData = computed<string[]>(() => props.options.xAxis?.data || [])
const yMin = computed<number>(() => props.options.yAxis?.min ?? 0)
const yMax = computed<number>(() => props.options.yAxis?.max ?? autoYMax())
const yLabelFormatter = computed<(v: number) => string>(() => props.options.yAxis?.formatter || ((v: number) => String(v)))

function autoYMax(): number {
  if (!series.value.length) return 100
  let max = -Infinity
  series.value.forEach(s => {
    if (!s._hidden && s.data) s.data.forEach(v => { if (v > max) max = v })
  })
  if (max <= 0) return 100
  const mag = Math.pow(10, Math.floor(Math.log10(max)))
  return Math.ceil(max / mag) * mag
}

const yTicks = computed<number[]>(() => {
  const count = props.options.yAxis?.splitNumber || 5
  const min = yMin.value
  const max = yMax.value
  const step = (max - min) / (count - 1)
  const ticks: number[] = []
  for (let i = 0; i < count; i++) {
    ticks.push(min + step * i)
  }
  return ticks
})

const AXIS_STYLE = {
  font: '11px -apple-system, BlinkMacSystemFont, sans-serif',
  color: 'rgba(230,232,239,0.55)',
  gridColor: 'rgba(255,255,255,0.06)',
  axisColor: 'rgba(255,255,255,0.12)'
}

/* ===== Drawing ===== */
function resize(): void {
  const el = wrap.value
  if (!el) return
  const rect = el.getBoundingClientRect()
  dpr = Math.min(window.devicePixelRatio || 1, 2)
  w = rect.width
  h = props.height ?? 360
  if (cvs.value) {
    cvs.value.width = w * dpr
    cvs.value.height = h * dpr
    cvs.value.style.width = w + 'px'
    cvs.value.style.height = h + 'px'
    ctx = cvs.value.getContext('2d')
    if (ctx) ctx.scale(dpr, dpr)
  }
  draw()
}

function chartW(): number { return w - PAD.left - PAD.right }
function chartH(): number { return h - PAD.top - PAD.bottom }
function xToPixel(index: number): number {
  const len = Math.max(1, xData.value.length - 1)
  return PAD.left + (index / len) * chartW()
}
function yToPixel(val: number): number {
  const range = yMax.value - yMin.value || 1
  return PAD.top + chartH() * (1 - (val - yMin.value) / range)
}

function drawGrid(): void {
  if (!ctx || w === 0) return
  ctx.clearRect(0, 0, w, h)

  const cw = chartW()
  const ch = chartH()

  ctx.textAlign = 'right'
  ctx.textBaseline = 'middle'
  yTicks.value.forEach(tick => {
    const y = yToPixel(tick)
    ctx!.beginPath()
    ctx!.strokeStyle = AXIS_STYLE.gridColor
    ctx!.lineWidth = 1
    ctx!.moveTo(PAD.left, y)
    ctx!.lineTo(PAD.left + cw, y)
    ctx!.stroke()

    ctx!.fillStyle = AXIS_STYLE.color
    ctx!.font = AXIS_STYLE.font
    ctx!.fillText(yLabelFormatter.value(tick), PAD.left - 8, y)
  })

  ctx.textAlign = 'center'
  ctx.textBaseline = 'top'
  xData.value.forEach((label, i) => {
    const x = xToPixel(i)
    ctx!.fillStyle = AXIS_STYLE.color
    ctx!.font = AXIS_STYLE.font
    ctx!.fillText(label, x, PAD.top + ch + 8)
  })

  ctx.beginPath()
  ctx.strokeStyle = AXIS_STYLE.axisColor
  ctx.lineWidth = 1
  ctx.moveTo(PAD.left, PAD.top)
  ctx.lineTo(PAD.left, PAD.top + ch)
  ctx.moveTo(PAD.left, PAD.top + ch)
  ctx.lineTo(PAD.left + cw, PAD.top + ch)
  ctx.stroke()
}

function drawSeries(progress = 1): void {
  if (!ctx) return
  const c = ctx

  series.value.forEach(s => {
    if (s._hidden || !s.data?.length) return

    const points: Point[] = s.data.map((v, i) => ({
      x: xToPixel(i),
      y: yToPixel(v),
      value: v
    }))

    const clipEnd = Math.max(1, Math.floor(points.length * progress))
    const visible = points.slice(0, clipEnd)

    // Area fill
    if (s._area && visible.length > 1) {
      const areaPath = new Path2D()
      if (s._smooth) {
        areaPath.moveTo(visible[0].x, visible[0].y)
        for (let i = 0; i < visible.length - 1; i++) {
          const [cp1, cp2] = controlPoints(visible, i)
          areaPath.bezierCurveTo(cp1.x, cp1.y, cp2.x, cp2.y, visible[i + 1].x, visible[i + 1].y)
        }
      } else {
        areaPath.moveTo(visible[0].x, visible[0].y)
        for (let i = 1; i < visible.length; i++) areaPath.lineTo(visible[i].x, visible[i].y)
      }
      areaPath.lineTo(visible[visible.length - 1].x, PAD.top + chartH())
      areaPath.lineTo(visible[0].x, PAD.top + chartH())
      areaPath.closePath()

      const grad = c.createLinearGradient(0, PAD.top, 0, PAD.top + chartH())
      grad.addColorStop(0, withAlpha(s._color, s._areaOpacity * 2.5))
      grad.addColorStop(1, withAlpha(s._color, 0))
      c.fillStyle = grad
      c.fill(areaPath)
    }

    // Line
    if (visible.length > 1) {
      c.beginPath()
      c.strokeStyle = s._color
      c.lineWidth = s._lineWidth
      c.lineJoin = 'round'
      c.lineCap = 'round'

      if (s._smooth) {
        c.moveTo(visible[0].x, visible[0].y)
        for (let i = 0; i < visible.length - 1; i++) {
          const [cp1, cp2] = controlPoints(visible, i)
          c.bezierCurveTo(cp1.x, cp1.y, cp2.x, cp2.y, visible[i + 1].x, visible[i + 1].y)
        }
      } else {
        c.moveTo(visible[0].x, visible[0].y)
        for (let i = 1; i < visible.length; i++) c.lineTo(visible[i].x, visible[i].y)
      }
      c.stroke()
    }

    // Dots
    visible.forEach(({ x, y }) => {
      c!.beginPath()
      c!.fillStyle = s._color
      c!.arc(x, y, 3.5, 0, Math.PI * 2)
      c!.fill()

      c!.beginPath()
      c!.fillStyle = withAlpha(s._color, 0.2)
      c!.arc(x, y, 6, 0, Math.PI * 2)
      c!.fill()
    })
  })
}

function draw(): void {
  drawGrid()
  drawSeries(animProgress)
}

function controlPoints(points: Point[], i: number): [Point, Point] {
  const p0 = points[i - 1] || points[i]
  const p1 = points[i]
  const p2 = points[i + 1]
  const p3 = points[i + 2] || p2
  const tension = 0.4
  const cp1: Point = {
    x: p1.x + (p2.x - p0.x) * tension,
    y: p1.y + (p2.y - p0.y) * tension,
    value: 0
  }
  const cp2: Point = {
    x: p2.x - (p3.x - p1.x) * tension,
    y: p2.y - (p3.y - p1.y) * tension,
    value: 0
  }
  return [cp1, cp2]
}

function withAlpha(hex: string, alpha: number): string {
  const r = parseInt(hex.slice(1, 3), 16)
  const g = parseInt(hex.slice(3, 5), 16)
  const b = parseInt(hex.slice(5, 7), 16)
  return `rgba(${r},${g},${b},${Math.max(0, Math.min(1, alpha))})`
}

/* ===== Animation ===== */
function startAnim(): void {
  animStart = performance.now()
  animProgress = 0
  if (animId !== null) cancelAnimationFrame(animId)
  function step(now: number): void {
    const elapsed = now - animStart
    animProgress = Math.min(1, elapsed / ANIM_DURATION)
    const eased = 1 - Math.pow(1 - animProgress, 3)
    drawGrid()
    drawSeries(eased)
    if (animProgress < 1) {
      animId = requestAnimationFrame(step)
    }
  }
  animId = requestAnimationFrame(step)
}

/* ===== Interaction ===== */
function onMove(e: MouseEvent): void {
  if (!cvs.value) return
  const rect = cvs.value.getBoundingClientRect()
  const mx = (e.clientX - rect.left) * (w / rect.width)
  const my = (e.clientY - rect.top) * (h / rect.height)

  const xIdx = findNearestX(mx)
  if (xIdx < 0) {
    tooltip.visible = false
    return
  }

  const px = xToPixel(xIdx)
  const title = xData.value[xIdx] || ''

  const items: TooltipItem[] = series.value
    .filter(s => !s._hidden && s.data && s.data[xIdx] !== undefined)
    .map(s => ({
      name: s.name || '',
      color: s._color,
      value: s.data[xIdx]
    }))

  if (!items.length) {
    tooltip.visible = false
    return
  }

  const tipX = px + 12
  const tipY = Math.max(0, my - 40)

  tooltip.visible = true
  tooltip.x = tipX
  tooltip.y = tipY
  tooltip.title = title
  tooltip.items = items

  draw()
  drawCrosshair(px)
}

function onLeave(): void {
  tooltip.visible = false
  draw()
}

function drawCrosshair(x: number): void {
  if (!ctx) return
  const c = ctx
  c.save()
  c.beginPath()
  c.strokeStyle = 'rgba(255,255,255,0.15)'
  c.lineWidth = 1
  c.setLineDash([4, 4])
  c.moveTo(x, PAD.top)
  c.lineTo(x, PAD.top + chartH())

  series.value.forEach(s => {
    if (s._hidden || !s.data) return
    const xIdx = findNearestX(x)
    if (xIdx >= 0 && s.data[xIdx] !== undefined) {
      const dotY = yToPixel(s.data[xIdx])
      c.beginPath()
      c.setLineDash([])
      c.fillStyle = s._color
      c.strokeStyle = '#fff'
      c.lineWidth = 2
      c.arc(x, dotY, 5, 0, Math.PI * 2)
      c.fill()
      c.stroke()
    }
  })
  c.stroke()
  c.restore()
}

function findNearestX(mx: number): number {
  if (!xData.value.length) return -1
  let nearest = 0
  let minDist = Infinity
  for (let i = 0; i < xData.value.length; i++) {
    const dist = Math.abs(xToPixel(i) - mx)
    if (dist < minDist) { minDist = dist; nearest = i }
  }
  if (minDist > chartW() / (xData.value.length - 1 || 1) * 1.5) return -1
  return nearest
}

function toggleSeries(i: number): void {
  series.value[i]._hidden = !series.value[i]._hidden
  draw()
}

/* ===== Lifecycle ===== */
onMounted(() => {
  resize()
  startAnim()
  const ro = new ResizeObserver(() => {
    resize()
  })
  if (wrap.value) {
    ro.observe(wrap.value)
  }
  onUnmounted(() => ro.disconnect())
})

watch(() => props.options, () => {
  resize()
  startAnim()
}, { deep: true })
</script>

<style scoped>
.line-chart-wrap {
  position: relative;
  width: 100%;
}

.line-chart-wrap canvas {
  display: block;
  width: 100%;
  cursor: crosshair;
}

/* Tooltip */
.chart-tooltip {
  position: absolute;
  pointer-events: none;
  z-index: 10;
  background: rgba(10, 16, 36, 0.96);
  border: 1px solid rgba(255, 255, 255, 0.12);
  border-radius: 8px;
  padding: 8px 12px;
  min-width: 120px;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.4);
}
.tooltip-title {
  font-size: 12px;
  color: rgba(230, 232, 239, 0.55);
  margin-bottom: 6px;
}
.tooltip-row {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  line-height: 1.8;
}
.tooltip-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  flex-shrink: 0;
}
.tooltip-name {
  color: rgba(230, 232, 239, 0.75);
}
.tooltip-value {
  margin-left: auto;
  color: #e6e8ef;
  font-weight: 600;
}

/* Legend */
.chart-legend {
  display: flex;
  justify-content: center;
  flex-wrap: wrap;
  gap: 16px;
  margin-top: 12px;
}
.legend-item {
  display: flex;
  align-items: center;
  gap: 5px;
  cursor: pointer;
  user-select: none;
  padding: 2px 6px;
  border-radius: 4px;
  transition: background 0.15s;
}
.legend-item:hover {
  background: rgba(255, 255, 255, 0.06);
}
.legend-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  flex-shrink: 0;
}
.legend-name {
  font-size: 12px;
  color: rgba(230, 232, 239, 0.75);
  transition: opacity 0.2s;
}
.legend-name.dimmed {
  opacity: 0.35;
}
</style>
