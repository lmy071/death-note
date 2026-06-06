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

<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'

const cvs = ref<HTMLCanvasElement | null>(null)
let ctx: CanvasRenderingContext2D | null = null
let animId: number | null = null
let w = 0, h = 0
let dpr = 1

let mx = -100, my = -100
let mouseInside = false

interface Particle {
  x: number
  y: number
  vx: number
  vy: number
  radius: number
  life: number
  decay: number
  color: string
  gravity: number
  update: () => void
  draw: () => void
}

const particles: Particle[] = []
const MAX_PARTICLES = 120

const PALETTE: string[] = [
  '#82b1ff',
  '#b388ff',
  '#8c9eff',
  '#84ffff',
  '#ff80ab',
  '#ffd740',
  '#69f0ae',
]

class ParticleImpl implements Particle {
  x: number
  y: number
  vx: number
  vy: number
  radius: number
  life: number
  decay: number
  color: string
  gravity: number

  constructor(x: number, y: number) {
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

  update(): void {
    this.x += this.vx
    this.y += this.vy
    this.vy += this.gravity
    this.vx *= 0.99
    this.life -= this.decay
    this.radius *= 0.995
  }

  draw(): void {
    if (!ctx) return
    const alpha = this.life
    ctx.globalAlpha = alpha
    ctx.beginPath()
    ctx.arc(this.x, this.y, Math.max(0.3, this.radius), 0, Math.PI * 2)
    ctx.fillStyle = this.color
    ctx.fill()
    ctx.beginPath()
    ctx.arc(this.x, this.y, Math.max(0.3, this.radius * 1.8), 0, Math.PI * 2)
    ctx.fillStyle = this.color
    ctx.globalAlpha = alpha * 0.18
    ctx.fill()
    ctx.globalAlpha = 1
  }
}

function spawnBurst(x: number, y: number, count: number): void {
  for (let i = 0; i < count; i++) {
    if (particles.length >= MAX_PARTICLES) particles.shift()
    particles.push(new ParticleImpl(x, y))
  }
}

function resize(): void {
  const el = cvs.value
  if (!el) return
  const rect = el.getBoundingClientRect()
  dpr = window.devicePixelRatio || 1
  w = rect.width
  h = rect.height
  el.width = w * dpr
  el.height = h * dpr
  ctx = el.getContext('2d')
  if (ctx) ctx.scale(dpr, dpr)
}

function render(): void {
  if (!ctx) return
  ctx.clearRect(0, 0, w, h)

  if (mouseInside && mx > 0 && my > 0 && mx < w && my < h) {
    spawnBurst(mx, my, 2)
  }

  for (let i = particles.length - 1; i >= 0; i--) {
    const p = particles[i]
    p.update()
    p.draw()
    if (p.life <= 0) particles.splice(i, 1)
  }

  animId = requestAnimationFrame(render)
}

function onMove(e: MouseEvent): void {
  const el = cvs.value
  if (!el) return
  const rect = el.getBoundingClientRect()
  mx = e.clientX - rect.left
  my = e.clientY - rect.top
}

function onEnter(e: MouseEvent | TouchEvent): void {
  mouseInside = true
  const el = cvs.value
  if (!el) return
  const rect = el.getBoundingClientRect()
  if (e instanceof MouseEvent) {
    mx = e.clientX - rect.left
    my = e.clientY - rect.top
  }
}

function onLeave(): void { mouseInside = false }

function onTouchMove(e: TouchEvent): void {
  const el = cvs.value
  if (!el) return
  const rect = el.getBoundingClientRect()
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
