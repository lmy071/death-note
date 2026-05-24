<template>
  <canvas
    ref="cvs"
    class="particle-canvas"
    @mousemove="onMove"
    @mouseenter="onEnter"
    @mouseleave="onLeave"
    @touchmove.prevent="onTouchMove"
    @touchstart.prevent="onEnter"
    @touchend="onLeave"
  ></canvas>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'

const cvs = ref(null)
let ctx = null
let animId = null
let w = 0, h = 0
let dpr = 1

// Mouse state
let mx = -100, my = -100
let mouseInside = false

// Particles array
const particles = []
const MAX_PARTICLES = 120

// Color palette — match dark theme
const PALETTE = [
  '#82b1ff', // blue
  '#b388ff', // purple
  '#8c9eff', // indigo
  '#84ffff', // cyan
  '#ff80ab', // pink
  '#ffd740', // amber
  '#69f0ae', // green
]

// Particle class
class Particle {
  constructor(x, y) {
    this.x = x
    this.y = y
    this.vx = (Math.random() - 0.5) * 3
    this.vy = (Math.random() - 0.5) * 3
    this.radius = Math.random() * 4 + 1.5
    this.life = 1
    this.decay = Math.random() * 0.02 + 0.008
    this.color = PALETTE[Math.floor(Math.random() * PALETTE.length)]
    this.gravity = 0.02
  }

  update() {
    this.x += this.vx
    this.y += this.vy
    this.vy += this.gravity
    this.vx *= 0.99 // slight friction
    this.life -= this.decay
    this.radius *= 0.995 // slight shrink
  }

  draw() {
    const alpha = this.life
    ctx.globalAlpha = alpha
    ctx.beginPath()
    ctx.arc(this.x, this.y, Math.max(0.3, this.radius), 0, Math.PI * 2)
    ctx.fillStyle = this.color
    ctx.fill()
    // Glow
    ctx.beginPath()
    ctx.arc(this.x, this.y, Math.max(0.3, this.radius * 1.8), 0, Math.PI * 2)
    ctx.fillStyle = this.color
    ctx.globalAlpha = alpha * 0.18
    ctx.fill()
    ctx.globalAlpha = 1
  }
}

function spawnBurst(x, y, count) {
  for (let i = 0; i < count; i++) {
    if (particles.length >= MAX_PARTICLES) particles.shift()
    particles.push(new Particle(x, y))
  }
}

function resize() {
  const el = cvs.value
  if (!el) return
  const rect = el.getBoundingClientRect()
  dpr = window.devicePixelRatio || 1
  w = rect.width
  h = rect.height
  el.width = w * dpr
  el.height = h * dpr
  ctx = el.getContext('2d')
  ctx.scale(dpr, dpr)
}

function render() {
  if (!ctx) return
  ctx.clearRect(0, 0, w, h)

  // Spawn particles when mouse is inside
  if (mouseInside && mx > 0 && my > 0 && mx < w && my < h) {
    spawnBurst(mx, my, 2)
  }

  // Update + draw
  for (let i = particles.length - 1; i >= 0; i--) {
    const p = particles[i]
    p.update()
    p.draw()
    if (p.life <= 0) particles.splice(i, 1)
  }

  animId = requestAnimationFrame(render)
}

function onMove(e) {
  const rect = cvs.value.getBoundingClientRect()
  mx = e.clientX - rect.left
  my = e.clientY - rect.top
}
function onEnter(e) {
  mouseInside = true
  const rect = cvs.value.getBoundingClientRect()
  mx = e.clientX - rect.left
  my = e.clientY - rect.top
}
function onLeave() { mouseInside = false }
function onTouchMove(e) {
  const rect = cvs.value.getBoundingClientRect()
  mx = e.touches[0].clientX - rect.left
  my = e.touches[0].clientY - rect.top
  mouseInside = true
}

onMounted(() => {
  resize()
  window.addEventListener('resize', resize)
  animId = requestAnimationFrame(render)
})
onUnmounted(() => {
  window.removeEventListener('resize', resize)
  if (animId) cancelAnimationFrame(animId)
})
</script>

<style scoped>
.particle-canvas {
  display: block;
  width: 100%;
  height: 200px;
  border-radius: 12px;
  background: rgba(0, 0, 0, 0.25);
}
</style>