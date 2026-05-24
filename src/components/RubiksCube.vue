<template>
  <div class="cube-container">
    <canvas
      ref="cvs"
      class="cube-canvas"
      @mousedown="onMouseDown"
      @mousemove="onMouseMove"
      @mouseup="onMouseUp"
      @mouseleave="onMouseUp"
      @touchstart.prevent="onTouchStart"
      @touchmove.prevent="onTouchMove"
      @touchend="onMouseUp"
    ></canvas>
    <div v-if="twistKeys.length" class="twist-bar">
      <button v-for="k in twistKeys" :key="k" class="twist-btn" @click.stop="twist(k)">{{ k }}</button>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, onUnmounted, watch, ref, reactive } from 'vue'

const props = defineProps({
  size: { type: Number, default: 280 },
  scale: { type: Number, default: 38 },
  autoRotate: { type: Boolean, default: true },
  showControls: { type: Boolean, default: false },
})

const cvs = ref(null)
let animId = null, ctx = null
let rotY = 0.5, rotX = -0.35
let dragging = false, autoRotate_ = props.autoRotate
let lastX = 0, lastY = 0, hasMoved = false

/* ════════════════════ COLORS ════════════════════ */
const COS30 = Math.cos(Math.PI / 6)
const SIN30 = Math.sin(Math.PI / 6)
const FACE_COLORS = {
  U: '#FFFFFF', D: '#FFD500',
  F: '#B71234', B: '#FF5800',
  R: '#0046AD', L: '#009B48',
}
const FACE_NAMES = ['U', 'D', 'F', 'B', 'R', 'L']
const FACE_NORMALS = { U: [0, 1, 0], D: [0, -1, 0], F: [0, 0, 1], B: [0, 0, -1], R: [1, 0, 0], L: [-1, 0, 0] }

/* face index → 4 quad vertices for each face of a unit cube at origin */
const QUAD_VERTICES = {
  R: [ [1, 0, 0], [1, 1, 0], [1, 1, 1], [1, 0, 1] ],  // x=1
  L: [ [0, 0, 1], [0, 1, 1], [0, 1, 0], [0, 0, 0] ],  // x=0
  U: [ [0, 1, 0], [1, 1, 0], [1, 1, 1], [0, 1, 1] ],  // y=1
  D: [ [0, 0, 1], [1, 0, 1], [1, 0, 0], [0, 0, 0] ],  // y=0
  F: [ [0, 0, 1], [1, 0, 1], [1, 1, 1], [0, 1, 1] ],  // z=1
  B: [ [0, 1, 0], [1, 1, 0], [1, 0, 0], [0, 0, 0] ],  // z=0
}

/* ════════════════════ CUBIE DATA ════════════════════ */
const cubies = reactive([])

function initSolved() {
  cubies.length = 0
  for (let ix = 0; ix < 3; ix++)
    for (let iy = 0; iy < 3; iy++)
      for (let iz = 0; iz < 3; iz++)
        cubies.push({
          ix, iy, iz,
          fc: {
            U: iy === 2 ? FACE_COLORS.U : null,
            D: iy === 0 ? FACE_COLORS.D : null,
            F: iz === 2 ? FACE_COLORS.F : null,
            B: iz === 0 ? FACE_COLORS.B : null,
            R: ix === 2 ? FACE_COLORS.R : null,
            L: ix === 0 ? FACE_COLORS.L : null,
          },
        })
}

function visibleFaces(c) {
  const out = []
  for (const f of FACE_NAMES) {
    if (c.fc[f] === null) continue
    const n = FACE_NORMALS[f]
    if (n[0] !== 0 && c.ix !== (n[0] > 0 ? 2 : 0)) continue
    if (n[1] !== 0 && c.iy !== (n[1] > 0 ? 2 : 0)) continue
    if (n[2] !== 0 && c.iz !== (n[2] > 0 ? 2 : 0)) continue
    out.push(f)
  }
  return out
}

/* ════════════════════ TWIST SYSTEM ════════════════════ */
let isTwisting = false
let twistInfo = null   // { axis: 'x'|'y'|'z', sign: 1|-1, level: 0|2, startTime, faceCycles, affected }
const TWIST_DURATION = 200

// face rotation cycles for each twist (clockwise looking from positive axis)
const CYCLES = {
  y_p1_l2: { cycle: ['F', 'R', 'B', 'L'] },  // U cw (looking from top)
  y_m1_l2: { cycle: ['F', 'L', 'B', 'R'] },  // U ccw
  y_m1_l0: { cycle: ['F', 'R', 'B', 'L'] },  // D cw (from below) → same as U ccw from top
  y_p1_l0: { cycle: ['F', 'L', 'B', 'R'] },  // D ccw → same as U cw
  x_p1_l2: { cycle: ['U', 'F', 'D', 'B'] },  // R cw
  x_m1_l2: { cycle: ['U', 'B', 'D', 'F'] },  // R ccw
  x_m1_l0: { cycle: ['U', 'F', 'D', 'B'] },  // L cw (looking from left)
  x_p1_l0: { cycle: ['U', 'B', 'D', 'F'] },  // L ccw
  z_p1_l2: { cycle: ['U', 'R', 'D', 'L'] },  // F cw
  z_m1_l2: { cycle: ['U', 'L', 'D', 'R'] },  // F ccw
  z_m1_l0: { cycle: ['U', 'R', 'D', 'L'] },  // B cw
  z_p1_l0: { cycle: ['U', 'L', 'D', 'R'] },  // B ccw
}

// position rotation for a twist (angle in radians, axis, sign, around center 1,1,1)
function rotateAroundAxis(rx, ry, rz, axis, signedAngle) {
  const cos = Math.cos(signedAngle), sin = Math.sin(signedAngle)
  if (axis === 'y') {
    return [cos * rx - sin * rz, ry, sin * rx + cos * rz]
  } else if (axis === 'x') {
    return [rx, cos * ry - sin * rz, sin * ry + cos * rz]
  } else { // z
    return [cos * rx - sin * ry, sin * rx + cos * ry, rz]
  }
}

function applyTwistToState(axis, sign, level) {
  const affected = []
  for (const c of cubies) {
    if ((axis === 'x' && c.ix === level) || (axis === 'y' && c.iy === level) || (axis === 'z' && c.iz === level))
      affected.push(c)
  }
  const angle = -sign * Math.PI / 2
  for (const c of affected) {
    const [nx, ny, nz] = rotateAroundAxis(c.ix - 1, c.iy - 1, c.iz - 1, axis, angle)
    c.ix = Math.round(nx + 1); c.iy = Math.round(ny + 1); c.iz = Math.round(nz + 1)
  }
  // Rotate face colors
  const key = `${axis}_${sign > 0 ? 'p1' : 'm1'}_l${level}`
  const cycle = CYCLES[key]?.cycle
  if (cycle) {
    for (const c of affected) {
      const [a, b, d, e] = cycle
      const tmp = c.fc[a]
      c.fc[a] = c.fc[e]
      c.fc[e] = c.fc[d]
      c.fc[d] = c.fc[b]
      c.fc[b] = tmp
    }
  }
}

function twist(key) {
  if (isTwisting) return
  const map = {
    U:  { axis: 'y', sign: 1,  level: 2 },
    "U'":{ axis: 'y', sign: -1, level: 2 },
    D:  { axis: 'y', sign: -1, level: 0 },
    "D'":{ axis: 'y', sign: 1,  level: 0 },
    R:  { axis: 'x', sign: 1,  level: 2 },
    "R'":{ axis: 'x', sign: -1, level: 2 },
    L:  { axis: 'x', sign: -1, level: 0 },
    "L'":{ axis: 'x', sign: 1,  level: 0 },
    F:  { axis: 'z', sign: 1,  level: 2 },
    "F'":{ axis: 'z', sign: -1, level: 2 },
    B:  { axis: 'z', sign: -1, level: 0 },
    "B'":{ axis: 'z', sign: 1,  level: 0 },
  }
  const t = map[key]
  if (!t) return

  const affected = []
  for (const c of cubies) {
    if ((t.axis === 'x' && c.ix === t.level) || (t.axis === 'y' && c.iy === t.level) || (t.axis === 'z' && c.iz === t.level))
      affected.push(c)
  }
  isTwisting = true; autoRotate_ = false
  const cycleKey = `${t.axis}_${t.sign > 0 ? 'p1' : 'm1'}_l${t.level}`
  twistInfo = { ...t, startTime: performance.now(), affected, faceCycles: CYCLES[cycleKey].cycle }
}

function scramble(count = 20) {
  const keys = ['U', "U'", 'D', "D'", 'R', "R'", 'L', "L'", 'F', "F'", 'B', "B'"]
  for (let i = 0; i < count; i++) {
    const { axis, sign, level } = ['U', 'D', 'R', 'L', 'F', 'B'].flatMap(k => {
      const cw = { U: ['y', 1, 2], D: ['y', -1, 0], R: ['x', 1, 2], L: ['x', -1, 0], F: ['z', 1, 2], B: ['z', -1, 0] }[k]
      return Math.random() > 0.5 ? [cw] : [[cw[0], -cw[1], cw[2]]] // random direction
    })[Math.floor(Math.random() * 12)]
    applyTwistToState(axis, sign, level)
  }
}

const twistKeys = computed(() => props.showControls ? ['U', "U'", 'D', "D'", 'R', "R'", 'L', "L'", 'F', "F'", 'B', "B'", '🔀'] : [])

/* ════════════════════ RENDER ════════════════════ */
const V = [[0, 0, 0], [1, 0, 0], [0, 1, 0], [1, 1, 0], [0, 0, 1], [1, 0, 1], [0, 1, 1], [1, 1, 1]]

function mulMat(a, b) {
  const r = [[0, 0, 0], [0, 0, 0], [0, 0, 0]]
  for (let i = 0; i < 3; i++)
    for (let j = 0; j < 3; j++)
      for (let k = 0; k < 3; k++) r[i][j] += a[i][k] * b[k][j]
  return r
}
function rotYMat(a) { const c = Math.cos(a), s = Math.sin(a); return [[c, 0, -s], [0, 1, 0], [s, 0, c]] }
function rotXMat(a) { const c = Math.cos(a), s = Math.sin(a); return [[1, 0, 0], [0, c, s], [0, -s, c]] }
function transform(pt, mat) {
  return [mat[0][0] * pt[0] + mat[0][1] * pt[1] + mat[0][2] * pt[2],
          mat[1][0] * pt[0] + mat[1][1] * pt[1] + mat[1][2] * pt[2],
          mat[2][0] * pt[0] + mat[2][1] * pt[1] + mat[2][2] * pt[2]]
}
function project(px, py, pz, cx, cy, s) {
  return { x: cx + (px - pz) * COS30 * s, y: cy + (px + pz) * SIN30 * s - py * s }
}
function shade(hex, k) {
  const r = parseInt(hex.slice(1, 3), 16), g = parseInt(hex.slice(3, 5), 16), b = parseInt(hex.slice(5, 7), 16)
  return `rgb(${Math.min(255, Math.round(r * k))},${Math.min(255, Math.round(g * k))},${Math.min(255, Math.round(b * k))})`
}

function render(now) {
  const el = cvs.value; if (!el) return
  ctx.clearRect(0, 0, el.width, el.height)

  // update twist animation
  let twistAngle = 0
  if (isTwisting && twistInfo) {
    const elapsed = now - twistInfo.startTime
    twistAngle = Math.min(1, elapsed / TWIST_DURATION) * (Math.PI / 2)
    if (elapsed >= TWIST_DURATION) {
      applyTwistToState(twistInfo.axis, twistInfo.sign, twistInfo.level)
      isTwisting = false; twistInfo = null; twistAngle = 0
      if (props.autoRotate) autoRotate_ = true
    }
  }

  if (autoRotate_ && !dragging) rotY += 0.005
  const Ry = rotYMat(rotY), Rx = rotXMat(rotX)
  const orbit = mulMat(Ry, Rx)
  const cx = el.width / 2, cy = el.height / 2 + 10
  const S = props.scale

  const toRender = []
  for (const c of cubies) {
    const verts = V.map(([vx, vy, vz]) => {
      let px = c.ix + vx - 1, py = c.iy + vy - 1, pz = c.iz + vz - 1
      if (twistInfo && twistInfo.affected.includes(c)) {
        const signedAngle = -twistInfo.sign * twistAngle
        ;[px, py, pz] = rotateAroundAxis(px, py, pz, twistInfo.axis, signedAngle)
      }
      const r = transform([px, py, pz], orbit)
      return { ...project(r[0], r[1], r[2], cx, cy, S), r }
    })
    let zd = 0
    for (const v of verts) zd += v.r[0] + v.r[1] + v.r[2]
    zd /= verts.length
    toRender.push({ c, verts, zd })
  }
  toRender.sort((a, b) => a.zd - b.zd)

  for (const { c, verts } of toRender) {
    // Use "after" colors during twist
    const fc = {}
    if (twistInfo && twistInfo.affected.includes(c) && twistInfo.faceCycles) {
      const [a, b, d, e] = twistInfo.faceCycles
      for (const f of FACE_NAMES) {
        if (f === a) fc[f] = c.fc[e]
        else if (f === b) fc[f] = c.fc[a]
        else if (f === d) fc[f] = c.fc[b]
        else if (f === e) fc[f] = c.fc[d]
        else fc[f] = c.fc[f]
      }
    } else {
      Object.assign(fc, c.fc)
    }

    for (const f of visibleFaces(c)) {
      const col = fc[f]
      if (!col) continue
      const rn = transform(FACE_NORMALS[f], orbit)
      const dot = rn[0] + rn[1] + rn[2]
      if (dot <= 0) continue

      const qv = QUAD_VERTICES[f]
      // compute projected quad corners
      const corners = qv.map(([qx, qy, qz]) => {
        let px = c.ix + qx - 1, py = c.iy + qy - 1, pz = c.iz + qz - 1
        if (twistInfo && twistInfo.affected.includes(c)) {
          const sa = -twistInfo.sign * twistAngle
          ;[px, py, pz] = rotateAroundAxis(px, py, pz, twistInfo.axis, sa)
        }
        return project(...transform([px, py, pz], orbit), cx, cy, S)
      })
      // check winding order
      if ((corners[1].x - corners[0].x) * (corners[2].y - corners[0].y) - (corners[1].y - corners[0].y) * (corners[2].x - corners[0].x) <= 0) continue

      ctx.beginPath(); ctx.moveTo(corners[0].x, corners[0].y)
      for (let i = 1; i < corners.length; i++) ctx.lineTo(corners[i].x, corners[i].y)
      ctx.closePath()

      const ndot = Math.max(0.25, (rn[1] + 1) / 2)
      const lightMap = { U: 1.0, F: 0.62, R: 0.48, L: 0.44, B: 0.52, D: 0.30 }
      ctx.fillStyle = shade(col, (lightMap[f] || 0.5) * (0.6 + 0.4 * ndot))
      ctx.fill()
      ctx.strokeStyle = 'rgba(0,0,0,0.18)'; ctx.lineWidth = 0.6; ctx.stroke()
    }
  }
  animId = requestAnimationFrame(render)
}

/* ════════════════════ INPUT ════════════════════ */
function onMouseDown(e) { dragging = true; lastX = e.clientX; lastY = e.clientY; hasMoved = false; autoRotate_ = false }
function onMouseMove(e) {
  if (!dragging) return
  const dx = e.clientX - lastX, dy = e.clientY - lastY
  if (Math.abs(dx) > 1 || Math.abs(dy) > 1) hasMoved = true
  rotY += dx * 0.008; rotX -= dy * 0.008
  rotX = Math.max(-1.2, Math.min(0.4, rotX))
  lastX = e.clientX; lastY = e.clientY
}
function onMouseUp() {
  dragging = false
  if (props.autoRotate && !isTwisting) autoRotate_ = true
}
function onTouchStart(e) { dragging = true; lastX = e.touches[0].clientX; lastY = e.touches[0].clientY; hasMoved = false; autoRotate_ = false }
function onTouchMove(e) {
  if (!dragging) return
  const dx = e.touches[0].clientX - lastX, dy = e.touches[0].clientY - lastY
  if (Math.abs(dx) > 1 || Math.abs(dy) > 1) hasMoved = true
  rotY += dx * 0.008; rotX -= dy * 0.008
  rotX = Math.max(-1.2, Math.min(0.4, rotX))
  lastX = e.touches[0].clientX; lastY = e.touches[0].clientY
}

/* ════════════════════ KEYBOARD ════════════════════ */
function onKeyDown(e) {
  if (isTwisting) return
  const map = {
    u: 'U', U: 'U', d: 'D', r: 'R', l: 'L', f: 'F', b: 'B',
  }
  let key = map[e.key]
  if (!key) return
  if (e.shiftKey) key += "'"
  twist(key)
}

onMounted(() => {
  initSolved()
  const el = cvs.value
  el.width = props.size; el.height = props.size
  ctx = el.getContext('2d')
  animId = requestAnimationFrame(render)
  window.addEventListener('keydown', onKeyDown)
})
onUnmounted(() => {
  if (animId) cancelAnimationFrame(animId)
  window.removeEventListener('keydown', onKeyDown)
})

/* expose scramble for parent */
defineExpose({ scramble, cubies })
</script>

<style scoped>
.cube-container { display: flex; flex-direction: column; align-items: center; gap: 8px; }
.cube-canvas { display: block; border-radius: 12px; cursor: grab; }
.cube-canvas:active { cursor: grabbing; }
.twist-bar { display: flex; flex-wrap: wrap; gap: 4px; justify-content: center; max-width: 320px; }
.twist-btn {
  font-size: 11px; font-weight: 700; font-family: ui-monospace, monospace;
  padding: 4px 9px; border-radius: 8px; border: 1px solid rgba(255,255,255,0.14);
  background: rgba(255,255,255,0.06); color: #e6e8ef; cursor: pointer;
  transition: background 0.12s;
}
.twist-btn:hover { background: rgba(130,177,255,0.18); border-color: rgba(130,177,255,0.4); }
</style>