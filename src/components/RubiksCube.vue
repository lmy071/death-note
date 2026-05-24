<template>
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
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'

const cvs = ref(null)
let animId = null
let rotY = 0.5       // Y-axis rotation angle
let rotX = -0.35     // X-axis (tilt) rotation angle
let dragging = false
let lastX = 0, lastY = 0

/* ---- Constants ---- */
const COS30 = Math.cos(Math.PI / 6)
const SIN30 = Math.sin(Math.PI / 6)
const S = 38  // unit scale in px

// Face colours (standard Rubik's cube)
const FACE_COLOR = {
  top:    '#FFFFFF',   // U – white
  bottom: '#FFD500',   // D – yellow
  front:  '#B71234',   // F – red
  back:   '#FF5800',   // B – orange
  right:  '#0046AD',   // R – blue
  left:   '#009B48',   // L – green
}

// Shading multipliers per-face norm for a 3D light-source effect
const LIGHT_TOP   = 1.0
const LIGHT_FRONT = 0.62
const LIGHT_RIGHT = 0.48
const LIGHT_LEFT  = 0.44
const LIGHT_BACK  = 0.52
const LIGHT_BOTTOM = 0.30

// Vertex indices for unit cube (0 … 7)
const V = [
  [0,0,0], [1,0,0], [0,1,0], [1,1,0],
  [0,0,1], [1,0,1], [0,1,1], [1,1,1],
]

// Face defs → vertex index order (counter-clockwise viewed from outside)
const FACES = {
  right:  { idx: [1,5,7,3], normal: [ 1, 0, 0] },
  left:   { idx: [0,2,6,4], normal: [-1, 0, 0] },
  top:    { idx: [2,3,7,6], normal: [ 0, 1, 0] },
  bottom: { idx: [0,4,5,1], normal: [ 0,-1, 0] },
  front:  { idx: [4,5,7,6], normal: [ 0, 0, 1] },
  back:   { idx: [0,1,3,2], normal: [ 0, 0,-1] },
}

/* ---- 3D maths ---- */
function mulMat(a, b) {
  const r = [[0,0,0],[0,0,0],[0,0,0]]
  for (let i = 0; i < 3; i++)
    for (let j = 0; j < 3; j++)
      for (let k = 0; k < 3; k++)
        r[i][j] += a[i][k] * b[k][j]
  return r
}

function rotMatrixY(a) {
  const c = Math.cos(a), s = Math.sin(a)
  return [[c,0,-s],[0,1,0],[s,0,c]]
}
function rotMatrixX(a) {
  const c = Math.cos(a), s = Math.sin(a)
  return [[1,0,0],[0,c,s],[0,-s,c]]
}

function transform(pt, mat) {
  return [
    mat[0][0]*pt[0] + mat[0][1]*pt[1] + mat[0][2]*pt[2],
    mat[1][0]*pt[0] + mat[1][1]*pt[1] + mat[1][2]*pt[2],
    mat[2][0]*pt[0] + mat[2][1]*pt[1] + mat[2][2]*pt[2],
  ]
}

function project(px, py, pz, cx, cy, scale) {
  return {
    x: cx + (px - pz) * COS30 * scale,
    y: cy + (px + pz) * SIN30 * scale - py * scale,
  }
}

function shade(hex, k) {
  const r = parseInt(hex.slice(1,3), 16)
  const g = parseInt(hex.slice(3,5), 16)
  const b = parseInt(hex.slice(5,7), 16)
  const rr = Math.min(255, Math.round(r * k))
  const gg = Math.min(255, Math.round(g * k))
  const bb = Math.min(255, Math.round(b * k))
  return `rgb(${rr},${gg},${bb})`
}

/* ---- Determine face colour from original cubie position ---- */
function faceColor(x, y, z, face) {
  if (face === 'top'    && y === 2) return FACE_COLOR.top
  if (face === 'bottom' && y === 0) return FACE_COLOR.bottom
  if (face === 'front'  && z === 2) return FACE_COLOR.front
  if (face === 'back'   && z === 0) return FACE_COLOR.back
  if (face === 'right'  && x === 2) return FACE_COLOR.right
  if (face === 'left'   && x === 0) return FACE_COLOR.left
  return null // not a surface face
}

function lightForFace(face) {
  switch (face) {
    case 'top':    return LIGHT_TOP
    case 'bottom': return LIGHT_BOTTOM
    case 'front':  return LIGHT_FRONT
    case 'back':   return LIGHT_BACK
    case 'right':  return LIGHT_RIGHT
    case 'left':   return LIGHT_LEFT
    default:       return 0.5
  }
}

/* ---- Rendering ---- */
function render() {
  const el = cvs.value
  if (!el) return
  const ctx = el.getContext('2d')
  const w = el.width, h = el.height
  ctx.clearRect(0, 0, w, h)

  // Auto-rotate when not dragging
  if (!dragging) rotY += 0.005

  // Build composite rotation matrix: R = Ry * Rx
  const Ry = rotMatrixY(rotY)
  const Rx = rotMatrixX(rotX)
  const R = mulMat(Ry, Rx)

  const cx = w / 2
  const cy = h / 2 + 10

  // Build cubie list → rotate each vertex, project, compute centroid depth
  const cubies = []
  const N = 3
  for (let ix = 0; ix < N; ix++) {
    for (let iy = 0; iy < N; iy++) {
      for (let iz = 0; iz < N; iz++) {
        const verts = V.map(([vx, vy, vz]) => {
          const p = [ix + vx - 1, iy + vy - 1, iz + vz - 1] // centre at origin
          const r = transform(p, R)
          return { ...project(r[0], r[1], r[2], cx, cy, S), r }
        })

        // centroid depth for painter's algorithm
        let zd = 0
        for (const v of verts) zd += v.r[0] + v.r[1] + v.r[2]
        zd /= verts.length

        cubies.push({ ix, iy, iz, verts, zd })
      }
    }
  }
  cubies.sort((a, b) => a.zd - b.zd)

  // Draw each cubie: only surface faces that face the camera
  for (const cb of cubies) {
    for (const [name, face] of Object.entries(FACES)) {
      const col = faceColor(cb.ix, cb.iy, cb.iz, name)
      if (!col) continue // not a surface face

      // Transform face normal
      const rn = transform(face.normal, R)

      // Back-face cull: normal must point toward camera (z > 0 for isometric top-right view)
      // Camera direction in rotated space ~ (1,1,1)
      const dot = rn[0] * 1 + rn[1] * 1 + rn[2] * 1
      if (dot <= 0) continue

      // 2D winding check (extra back-face culling)
      const iv = face.idx
      const p0 = cb.verts[iv[0]], p1 = cb.verts[iv[1]], p2 = cb.verts[iv[2]]
      const cross = (p1.x - p0.x) * (p2.y - p0.y) - (p1.y - p0.y) * (p2.x - p0.x)
      if (cross <= 0) continue

      // Draw face
      ctx.beginPath()
      ctx.moveTo(p0.x, p0.y)
      for (let i = 1; i < iv.length; i++) ctx.lineTo(cb.verts[iv[i]].x, cb.verts[iv[i]].y)
      ctx.closePath()

      const light = lightForFace(name)
      // Adjust light based on rotated normal (how much it faces the light)
      const ndot = Math.max(0.25, (rn[1] + 1) / 2) // normal vs up-light
      const finalLight = light * (0.6 + 0.4 * ndot)
      ctx.fillStyle = shade(col, finalLight)
      ctx.fill()

      // Subtle edge
      ctx.strokeStyle = 'rgba(0,0,0,0.18)'
      ctx.lineWidth = 0.6
      ctx.stroke()
    }
  }

  animId = requestAnimationFrame(render)
}

/* ---- Interaction ---- */
function onMouseDown(e) { dragging = true; lastX = e.clientX; lastY = e.clientY }
function onMouseMove(e) {
  if (!dragging) return
  const dx = e.clientX - lastX
  const dy = e.clientY - lastY
  rotY += dx * 0.008
  rotX -= dy * 0.008
  rotX = Math.max(-1.2, Math.min(0.4, rotX)) // clamp tilt
  lastX = e.clientX
  lastY = e.clientY
}
function onMouseUp() { dragging = false }

function onTouchStart(e) {
  dragging = true
  lastX = e.touches[0].clientX
  lastY = e.touches[0].clientY
}
function onTouchMove(e) {
  if (!dragging) return
  const dx = e.touches[0].clientX - lastX
  const dy = e.touches[0].clientY - lastY
  rotY += dx * 0.008
  rotX -= dy * 0.008
  rotX = Math.max(-1.2, Math.min(0.4, rotX))
  lastX = e.touches[0].clientX
  lastY = e.touches[0].clientY
}

onMounted(() => {
  const el = cvs.value
  el.width = 280
  el.height = 280
  animId = requestAnimationFrame(render)
})

onUnmounted(() => {
  if (animId) cancelAnimationFrame(animId)
})
</script>

<style scoped>
.cube-canvas {
  display: block;
  width: 100%;
  border-radius: 12px;
  cursor: grab;
}
.cube-canvas:active {
  cursor: grabbing;
}
</style>