<template>
  <div class="detail">
    <header class="detail-bar">
      <router-link to="/" class="back-btn">← 返回首页</router-link>
      <h1 class="detail-title">粒子特效</h1>
      <span class="detail-badge">Canvas 2D</span>
    </header>

    <main class="detail-body">
      <section class="canvas-stage">
        <canvas
          ref="cvs"
          class="main-canvas"
          @mousemove="onMove"
          @mouseenter="handleMouseEnter"
          @mouseleave="handleMouseLeave"
          @touchmove.prevent="onTouchMove"
          @touchstart.prevent="handleTouchStart"
          @touchend="handleTouchEnd"
        ></canvas>
      </section>

      <section class="info-panel">
        <div class="info-item">
          <span class="info-icon">🎯</span>
          <div>
            <h4>触发方式</h4>
            <p>鼠标移入画布即持续生成彩色粒子流</p>
          </div>
        </div>
        <div class="info-item">
          <span class="info-icon">🎨</span>
          <div>
            <h4>配色方案</h4>
            <p>蓝 · 紫 · 靛 · 青 · 粉 · 金 · 绿</p>
          </div>
        </div>
        <div class="info-item">
          <span class="info-icon">⚡</span>
          <div>
            <h4>粒子物理</h4>
            <p>随机扩散 · 重力下沉 · 摩擦衰减 · 光晕叠加</p>
          </div>
        </div>
      </section>
    </main>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'

const cvs = ref<HTMLCanvasElement | null>(null)
let ctx: CanvasRenderingContext2D | null = null
let animId: number | null = null
let w = 0, h = 0
let dpr = 1

let mx = -100, my = -100
let mouseInside: boolean = false

function handleMouseEnter(): void { mouseInside = true }
function handleMouseLeave(): void { mouseInside = false }
function handleTouchStart(): void { mouseInside = true }
function handleTouchEnd(): void { mouseInside = false }

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
const MAX_PARTICLES = 180

const PALETTE: string[] = [
  '#82b1ff', '#b388ff', '#8c9eff',
  '#84ffff', '#ff80ab', '#ffd740', '#69f0ae',
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
    this.x = x; this.y = y
    const ang = Math.random() * Math.PI * 2
    const spd = Math.random() * 3.5
    this.vx = Math.cos(ang) * spd
    this.vy = Math.sin(ang) * spd
    this.radius = Math.random() * 5 + 1.5
    this.life = 1
    this.decay = Math.random() * 0.018 + 0.006
    this.color = PALETTE[Math.floor(Math.random() * PALETTE.length)]
    this.gravity = 0.018
  }

  update(): void {
    this.x += this.vx; this.y += this.vy
    this.vy += this.gravity
    this.vx *= 0.99
    this.life -= this.decay
    this.radius *= 0.994
  }

  draw(): void {
    if (!ctx) return
    const a = Math.max(0, this.life)
    ctx.globalAlpha = a
    ctx.beginPath()
    ctx.arc(this.x, this.y, Math.max(0.2, this.radius), 0, Math.PI * 2)
    ctx.fillStyle = this.color
    ctx.fill()
    ctx.beginPath()
    ctx.arc(this.x, this.y, Math.max(0.2, this.radius * 2), 0, Math.PI * 2)
    ctx.fillStyle = this.color
    ctx.globalAlpha = a * 0.2
    ctx.fill()
    ctx.globalAlpha = 1
  }
}

function spawn(x: number, y: number, n: number): void {
  for (let i = 0; i < n; i++) {
    if (particles.length >= MAX_PARTICLES) particles.shift()
    particles.push(new ParticleImpl(x, y))
  }
}

function resize(): void {
  const el = cvs.value
  if (!el) return
  const rect = el.parentElement!.getBoundingClientRect()
  dpr = window.devicePixelRatio || 1
  w = rect.width
  h = 480
  el.width = w * dpr
  el.height = h * dpr
  ctx = el.getContext('2d')
  if (ctx) ctx.scale(dpr, dpr)
}

function render(): void {
  if (!ctx) return
  ctx.clearRect(0, 0, w, h)

  if (mouseInside && mx > 0 && my > 0 && mx < w && my < h) {
    spawn(mx, my, 3)
  }

  for (let i = particles.length - 1; i >= 0; i--) {
    particles[i].update()
    particles[i].draw()
    if (particles[i].life <= 0) particles.splice(i, 1)
  }

  animId = requestAnimationFrame(render)
}

function onMove(e: MouseEvent): void {
  const el = cvs.value
  if (!el) return
  const r = el.getBoundingClientRect()
  mx = e.clientX - r.left; my = e.clientY - r.top
}

function onTouchMove(e: TouchEvent): void {
  const el = cvs.value
  if (!el) return
  const r = el.getBoundingClientRect()
  mx = e.touches[0].clientX - r.left; my = e.touches[0].clientY - r.top
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
.detail {
  min-height: 100vh;
  width: 100vw;
  background: radial-gradient(circle at top, #151b2f 0, #050816 55%, #02010a 100%);
  display: flex;
  flex-direction: column;
  align-items: center;
}
.detail-bar {
  width: 100%;
  max-width: 960px;
  padding: 20px 24px 16px;
  display: flex;
  align-items: center;
  gap: 16px;
}
.back-btn {
  font-size: 14px;
  color: rgba(130,177,255,0.85);
  text-decoration: none;
  font-weight: 600;
  transition: color 0.15s;
  flex-shrink: 0;
}
.back-btn:hover { color: rgba(160,200,255,1); }
.detail-title { font-size: 22px; font-weight: 750; color: #e6e8ef; margin: 0; }
.detail-badge {
  font-size: 12px;
  font-weight: 650;
  padding: 3px 10px;
  border-radius: 999px;
  background: rgba(130,177,255,0.14);
  color: rgba(200,218,255,0.95);
  border: 1px solid rgba(130,177,255,0.25);
}
.detail-body {
  flex: 1;
  width: 100%;
  max-width: 960px;
  padding: 0 24px 40px;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 32px;
}
.canvas-stage {
  width: 100%;
  max-width: 900px;
  display: flex;
  justify-content: center;
  border-radius: 16px;
  overflow: hidden;
  border: 1px solid rgba(255,255,255,0.08);
  background: rgba(0,0,0,0.3);
}
.main-canvas {
  display: block;
  width: 100%;
  height: 480px;
  border-radius: 14px;
}
.info-panel {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
  gap: 16px;
  width: 100%;
  max-width: 720px;
}
.info-item {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  padding: 16px;
  border-radius: 14px;
  background: rgba(10,16,32,0.95);
  border: 1px solid rgba(255,255,255,0.08);
}
.info-icon { font-size: 24px; line-height: 1; flex-shrink: 0; margin-top: 2px; }
.info-item h4 { margin: 0 0 4px; font-size: 14px; font-weight: 700; color: #e6e8ef; }
.info-item p { margin: 0; font-size: 13px; line-height: 1.5; color: rgba(230,232,239,0.65); }
</style>
