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

<script setup>
import { ref, reactive, computed, onMounted, onUnmounted, watch } from 'vue'

const props = defineProps({
  options: { type: Object, default: () => ({}) },
  height: { type: Number, default: 360 }
})

const cvs = ref(null)
const wrap = ref(null)
let ctx = null
let w = 0
let h = 0
let dpr = 1
let animId = null
let animProgress = 0  // 0 → 1
let animStart = 0
const ANIM_DURATION = 800 // ms

// Padding for chart area
const PAD = { top: 20, right: 20, bottom: 40, left: 50 }

// Tooltip state
const tooltip = reactive({ visible: false, x: 0, y: 0, title: '', items: [] })

// Derive normalized series with colors
const palette = [
  '#82b1ff', '#ff80ab', '#69f0ae', '#ffd740', '#b388ff',
  '#84ffff', '#ff6e40', '#40c4ff', '#ea80fc', '#b2ff59'
]

const series = computed(() => {
  const raw = props.options.series || []
  return raw.map((s, i) => ({
    ...s,
    _color: s.color || palette[i % palette.length],
    _hidden: s._hidden || false,
    _smooth: s.smooth !== false,
    _area: s.area || false,
    _lineWidth: s.lineWidth || 2,
    _areaOpacity: s.areaOpacity || 0.15
  }))
})

const xData = computed(() => props.options.xAxis?.data || [])
const yMin = computed(() => props.options.yAxis?.min ?? 0)
const yMax = computed(() => props.options.yAxis?.max ?? autoYMax())
const yLabelFormatter = computed(() => props.options.yAxis?.formatter || (v => v))

function autoYMax() {
  if (!series.value.length) return 100
  let max = -Infinity
  series.value.forEach(s => {
    if (!s._hidden && s.data) s.data.forEach(v => { if (v > max) max = v })
  })
  if (max <= 0) return 100
  // Round up to nice number
  const mag = Math.pow(10, Math.floor(Math.log10(max)))
  return Math.ceil(max / mag) * mag
}

// Grid lines
const yTicks = computed(() => {
  const count = props.options.yAxis?.splitNumber || 5
  const min = yMin.value
  const max = yMax.value
  const step = (max - min) / (count - 1)
  const ticks = []
  for (let i = 0; i < count; i++) {
    ticks.push(min + step * i)
  }
  return ticks
})

// Axis text styling
const AXIS_STYLE = {
  font: '11px -apple-system, BlinkMacSystemFont, sans-serif',
  color: 'rgba(230,232,239,0.55)',
  gridColor: 'rgba(255,255,255,0.06)',
  axisColor: 'rgba(255,255,255,0.12)'
}

/* ===== Drawing ===== */
function resize() {
  const el = wrap.value
  if (!el) return
  const rect = el.getBoundingClientRect()
  dpr = Math.min(window.devicePixelRatio || 1, 2)
  w = rect.width
  h = props.height
  cvs.value.width = w * dpr
  cvs.value.height = h * dpr
  cvs.value.style.width = w + 'px'
  cvs.value.style.height = h + 'px'
  ctx = cvs.value.getContext('2d')
  ctx.scale(dpr, dpr)
  draw()
}

function chartW() { return w - PAD.left - PAD.right }
function chartH() { return h - PAD.top - PAD.bottom }
function xToPixel(index) {
  const len = Math.max(1, xData.value.length - 1)
  return PAD.left + (index / len) * chartW()
}
function yToPixel(val) {
  const range = yMax.value - yMin.value || 1
  return PAD.top + chartH() * (1 - (val - yMin.value) / range)
}

function drawGrid() {
  if (!ctx || w === 0) return
  ctx.clearRect(0, 0, w, h)

  const cw = chartW()
  const ch = chartH()

  // Y axis grid lines + labels
  ctx.textAlign = 'right'
  ctx.textBaseline = 'middle'
  yTicks.value.forEach(tick => {
    const y = yToPixel(tick)
    // Grid line
    ctx.beginPath()
    ctx.strokeStyle = AXIS_STYLE.gridColor
    ctx.lineWidth = 1
    ctx.moveTo(PAD.left, y)
    ctx.lineTo(PAD.left + cw, y)
    ctx.stroke()

    // Label
    ctx.fillStyle = AXIS_STYLE.color
    ctx.font = AXIS_STYLE.font
    ctx.fillText(yLabelFormatter.value(tick), PAD.left - 8, y)
  })

  // X axis labels
  ctx.textAlign = 'center'
  ctx.textBaseline = 'top'
  xData.value.forEach((label, i) => {
    const x = xToPixel(i)
    ctx.fillStyle = AXIS_STYLE.color
    ctx.font = AXIS_STYLE.font
    ctx.fillText(label, x, PAD.top + ch + 8)
  })

  // Axis lines
  ctx.beginPath()
  ctx.strokeStyle = AXIS_STYLE.axisColor
  ctx.lineWidth = 1
  // Y axis
  ctx.moveTo(PAD.left, PAD.top)
  ctx.lineTo(PAD.left, PAD.top + ch)
  // X axis
  ctx.moveTo(PAD.left, PAD.top + ch)
  ctx.lineTo(PAD.left + cw, PAD.top + ch)
  ctx.stroke()
}

function drawSeries(progress = 1) {
  if (!ctx) return

  series.value.forEach(s => {
    if (s._hidden || !s.data?.length) return

    const points = s.data.map((v, i) => ({
      x: xToPixel(i),
      y: yToPixel(v),
      value: v
    }))

    const clipEnd = Math.max(1, Math.floor(points.length * progress))
    const visible = points.slice(0, clipEnd)

    // Area fill
    if (s._area && visible.length > 1) {
      const areaPath = new Path2D()
      // Top line
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
      // Down to baseline
      areaPath.lineTo(visible[visible.length - 1].x, PAD.top + chartH())
      areaPath.lineTo(visible[0].x, PAD.top + chartH())
      areaPath.closePath()

      // Gradient fill
      const grad = ctx.createLinearGradient(0, PAD.top, 0, PAD.top + chartH())
      grad.addColorStop(0, withAlpha(s._color, s._areaOpacity * 2.5))
      grad.addColorStop(1, withAlpha(s._color, 0))
      ctx.fillStyle = grad
      ctx.fill(areaPath)
    }

    // Line
    if (visible.length > 1) {
      ctx.beginPath()
      ctx.strokeStyle = s._color
      ctx.lineWidth = s._lineWidth
      ctx.lineJoin = 'round'
      ctx.lineCap = 'round'

      if (s._smooth) {
        ctx.moveTo(visible[0].x, visible[0].y)
        for (let i = 0; i < visible.length - 1; i++) {
          const [cp1, cp2] = controlPoints(visible, i)
          ctx.bezierCurveTo(cp1.x, cp1.y, cp2.x, cp2.y, visible[i + 1].x, visible[i + 1].y)
        }
      } else {
        ctx.moveTo(visible[0].x, visible[0].y)
        for (let i = 1; i < visible.length; i++) ctx.lineTo(visible[i].x, visible[i].y)
      }
      ctx.stroke()
    }

    // Dots
    visible.forEach(({ x, y }) => {
      ctx.beginPath()
      ctx.fillStyle = s._color
      ctx.arc(x, y, 3.5, 0, Math.PI * 2)
      ctx.fill()

      // Outer glow ring
      ctx.beginPath()
      ctx.fillStyle = withAlpha(s._color, 0.2)
      ctx.arc(x, y, 6, 0, Math.PI * 2)
      ctx.fill()
    })
  })
}

function draw() {
  drawGrid()
  drawSeries(animProgress)
}

// Catmull-Rom → Bezier control points
function controlPoints(points, i) {
  const p0 = points[i - 1] || points[i]
  const p1 = points[i]
  const p2 = points[i + 1]
  const p3 = points[i + 2] || p2
  const tension = 0.4
  const cp1 = {
    x: p1.x + (p2.x - p0.x) * tension,
    y: p1.y + (p2.y - p0.y) * tension
  }
  const cp2 = {
    x: p2.x - (p3.x - p1.x) * tension,
    y: p2.y - (p3.y - p1.y) * tension
  }
  return [cp1, cp2]
}

function withAlpha(hex, alpha) {
  const r = parseInt(hex.slice(1, 3), 16)
  const g = parseInt(hex.slice(3, 5), 16)
  const b = parseInt(hex.slice(5, 7), 16)
  return `rgba(${r},${g},${b},${Math.max(0, Math.min(1, alpha))})`
}

/* ===== Animation ===== */
function startAnim() {
  animStart = performance.now()
  animProgress = 0
  cancelAnimationFrame(animId)
  function step(now) {
    const elapsed = now - animStart
    animProgress = Math.min(1, elapsed / ANIM_DURATION)
    // Ease out cubic
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
function onMove(e) {
  if (!cvs.value) return
  const rect = cvs.value.getBoundingClientRect()
  const mx = (e.clientX - rect.left) * (w / rect.width)  // account for CSS scale
  const my = (e.clientY - rect.top) * (h / rect.height)

  // Find nearest data point
  const xIdx = findNearestX(mx)
  if (xIdx < 0) {
    tooltip.visible = false
    return
  }

  const px = xToPixel(xIdx)
  const title = xData.value[xIdx] || ''

  const items = series.value
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

  // Position tooltip
  const tipX = px + 12
  const tipY = Math.max(0, my - 40)

  tooltip.visible = true
  tooltip.x = tipX
  tooltip.y = tipY
  tooltip.title = title
  tooltip.items = items

  // Draw crosshair
  draw()
  drawCrosshair(px)
}

function onLeave() {
  tooltip.visible = false
  draw()
}

function drawCrosshair(x) {
  if (!ctx) return
  ctx.save()
  ctx.beginPath()
  ctx.strokeStyle = 'rgba(255,255,255,0.15)'
  ctx.lineWidth = 1
  ctx.setLineDash([4, 4])
  ctx.moveTo(x, PAD.top)
  ctx.lineTo(x, PAD.top + chartH())

  // Highlight dot on each series
  series.value.forEach(s => {
    if (s._hidden || !s.data) return
    const xIdx = findNearestX(x)
    if (xIdx >= 0 && s.data[xIdx] !== undefined) {
      const dotY = yToPixel(s.data[xIdx])
      ctx.beginPath()
      ctx.setLineDash([])
      ctx.fillStyle = s._color
      ctx.strokeStyle = '#fff'
      ctx.lineWidth = 2
      ctx.arc(x, dotY, 5, 0, Math.PI * 2)
      ctx.fill()
      ctx.stroke()
    }
  })
  ctx.stroke()
  ctx.restore()
}

function findNearestX(mx) {
  if (!xData.value.length) return -1
  let nearest = 0
  let minDist = Infinity
  for (let i = 0; i < xData.value.length; i++) {
    const dist = Math.abs(xToPixel(i) - mx)
    if (dist < minDist) { minDist = dist; nearest = i }
  }
  // Only snap if within reasonable distance
  if (minDist > chartW() / (xData.value.length - 1 || 1) * 1.5) return -1
  return nearest
}

function toggleSeries(i) {
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
  ro.observe(wrap.value)
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
