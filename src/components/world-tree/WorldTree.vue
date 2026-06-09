<template>
  <div ref="container" class="world-tree-3d">
    <div v-if="hoveredBranch" class="branch-tooltip" :style="tooltipStyle">
      <div class="branch-tooltip__name">{{ hoveredBranch.label }}</div>
      <div v-if="hoveredBranch.desc" class="branch-tooltip__desc">{{ hoveredBranch.desc }}</div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import * as THREE from 'three'
import type { PageInfo, HitArea } from './types'
import { createRng } from './canvasUtils'
import { buildTree3D } from './tree3dBuilder'
import { createTreeMaterials, type TreeMaterials } from './tree3dMaterials'
import { animateTree3D } from './tree3dAnimator'

const emit = defineEmits<{ (e: 'ready'): void }>()
const router = useRouter()
const container = ref<HTMLDivElement | null>(null)
const hoveredBranch = ref<HitArea | null>(null)
const tooltipPos = ref<{ x: number; y: number }>({ x: 0, y: 0 })
const tooltipStyle = computed(() => ({
  left: `${tooltipPos.value.x + 14}px`,
  top: `${tooltipPos.value.y - 10}px`,
}))

const realPages: PageInfo[] = [
  { label: 'LeetCode 题解', route: '/code/leet-code', desc: '算法题解集' },
  { label: '笔记', route: '/md/md-note', desc: '技术笔记' },
  { label: '粒子特效', route: '/fun/particle-canvas', desc: 'Canvas 粒子动画' },
  { label: '折线图', route: '/fun/line-chart', desc: '数据可视化' },
]

// ---- Three.js state ----
let scene: THREE.Scene
let camera: THREE.OrthographicCamera
let renderer: THREE.WebGLRenderer
let animId: number | null = null
let growthProgress = 0
let startTime: number | null = null
let fullyGrown = false
let mouseX = 0, mouseY = 0

// Cached isometric base position (avoids per-frame allocation)
const ISO_BASE = new THREE.Vector3(
  40 * Math.cos(Math.PI / 6),
  40 * Math.sin(Math.PI / 6),
  40 * Math.cos(Math.PI / 6),
)

// ---- Tree objects ----
let treeGroup: THREE.Group
let dollMeshes: THREE.Object3D[] = []  // clickable dolls
let dollData: HitArea[] = []
let materials: TreeMaterials
let grassUniforms: { uTime: { value: number }; uGrowth: { value: number } }

const raycaster = new THREE.Raycaster()
const pointer = new THREE.Vector2(-999, -999)

// ---- Init ----

function init(): void {
  const el = container.value!
  const w = el.clientWidth, h = el.clientHeight

  // Scene
  scene = new THREE.Scene()
  scene.fog = new THREE.FogExp2(0x0a1020, 0.008)

  // 2.5D Isometric Camera (Orthographic)
  const frustumSize = 30
  const aspect = w / h
  camera = new THREE.OrthographicCamera(
    frustumSize * aspect / -2,
    frustumSize * aspect / 2,
    frustumSize / 2,
    frustumSize / -2,
    0.1, 200,
  )
  // Classic isometric angle: ~35.264° elevation, 45° rotation
  const isoDist = 40
  camera.position.set(isoDist * Math.cos(Math.PI / 6), isoDist * Math.sin(Math.PI / 6), isoDist * Math.cos(Math.PI / 6))
  camera.lookAt(0, 6, 0)

  // Renderer
  renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true })
  renderer.setSize(w, h)
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2))
  renderer.shadowMap.enabled = true
  renderer.shadowMap.type = THREE.PCFSoftShadowMap
  renderer.toneMapping = THREE.ACESFilmicToneMapping
  renderer.toneMappingExposure = 1.2
  el.appendChild(renderer.domElement)

  // Lights
  const ambient = new THREE.AmbientLight(0x1a1a3a, 0.6)
  scene.add(ambient)

  const dirLight = new THREE.DirectionalLight(0xffeedd, 1.2)
  dirLight.position.set(8, 20, 10)
  dirLight.castShadow = true
  dirLight.shadow.mapSize.set(1024, 1024)
  dirLight.shadow.camera.near = 0.5
  dirLight.shadow.camera.far = 60
  dirLight.shadow.camera.left = -15
  dirLight.shadow.camera.right = 15
  dirLight.shadow.camera.top = 20
  dirLight.shadow.camera.bottom = -5
  scene.add(dirLight)

  const pointLight = new THREE.PointLight(0xd4a017, 1.5, 30)
  pointLight.position.set(0, 12, 2)
  scene.add(pointLight)

  const rimLight = new THREE.DirectionalLight(0x4488ff, 0.3)
  rimLight.position.set(-5, 10, -8)
  scene.add(rimLight)

  // Materials
  materials = createTreeMaterials()

  // Build tree
  const seed = Math.floor(Math.random() * 2147483646) + 1
  const rng = createRng(seed)
  const buildResult = buildTree3D(rng, realPages, materials)
  treeGroup = buildResult.group
  dollMeshes = buildResult.dollMeshes
  dollData = buildResult.dollData
  grassUniforms = buildResult.grassUniforms
  scene.add(treeGroup)

  // Growth: start all meshes at scale 0
  treeGroup.traverse((child) => {
    if (child.userData.growthOrder !== undefined) {
      child.scale.set(0, 0, 0)
    }
  })

  // Mouse
  el.addEventListener('mousemove', onMouseMove)
  el.addEventListener('click', onClick)
  el.addEventListener('mouseleave', onMouseLeave)
}

// ---- Animation loop ----

const GROWTH_MS = 4200

function animate(ts: number): void {
  animId = requestAnimationFrame(animate)

  if (!startTime) startTime = ts
  const elapsed = ts - startTime
  const t = Math.min(1, elapsed / GROWTH_MS)
  growthProgress = 1 - Math.pow(1 - t, 3)

  if (t >= 1 && !fullyGrown) {
    fullyGrown = true
    emit('ready')
  }

  // Animate tree
  animateTree3D(treeGroup, growthProgress, ts * 0.001, grassUniforms)

  // 2.5D: subtle camera pan following mouse (very gentle)
  const targetCamOffsetX = mouseX * 2
  const targetCamOffsetY = mouseY * 1
  camera.position.x = ISO_BASE.x + targetCamOffsetX
  camera.position.y = ISO_BASE.y + targetCamOffsetY
  camera.lookAt(0, 6, 0)

  renderer.render(scene, camera)
}

// ---- Interaction ----

function onMouseMove(e: MouseEvent): void {
  const el = container.value!
  const rect = el.getBoundingClientRect()
  mouseX = ((e.clientX - rect.left) / rect.width - 0.5) * 2
  mouseY = -((e.clientY - rect.top) / rect.height - 0.5) * 2

  tooltipPos.value = { x: e.clientX, y: e.clientY }

  if (!fullyGrown || dollMeshes.length === 0) return

  pointer.x = mouseX
  pointer.y = mouseY
  raycaster.setFromCamera(pointer, camera)

  const intersects = raycaster.intersectObjects(dollMeshes, false)
  if (intersects.length > 0) {
    const obj = intersects[0].object
    const idx = dollMeshes.indexOf(obj)
    if (idx >= 0 && idx < dollData.length) {
      hoveredBranch.value = dollData[idx]
      renderer.domElement.style.cursor = 'pointer'
      return
    }
  }
  hoveredBranch.value = null
  renderer.domElement.style.cursor = 'default'
}

function onClick(e: MouseEvent): void {
  if (!fullyGrown) return
  if (hoveredBranch.value) {
    router.push(hoveredBranch.value.route)
  }
}

function onMouseLeave(): void {
  hoveredBranch.value = null
  mouseX = 0
  mouseY = 0
  renderer.domElement.style.cursor = 'default'
}

// ---- Resize ----

function onResize(): void {
  const el = container.value
  if (!el || !renderer) return
  const w = el.clientWidth, h = el.clientHeight
  const aspect = w / h
  const frustumSize = 30
  camera.left = frustumSize * aspect / -2
  camera.right = frustumSize * aspect / 2
  camera.top = frustumSize / 2
  camera.bottom = frustumSize / -2
  camera.updateProjectionMatrix()
  renderer.setSize(w, h)
}

// ---- Lifecycle ----

onMounted(() => {
  init()
  window.addEventListener('resize', onResize)
  animId = requestAnimationFrame(animate)
})

onUnmounted(() => {
  window.removeEventListener('resize', onResize)
  if (animId) cancelAnimationFrame(animId)
  renderer?.dispose()
})
</script>

<style scoped>
.world-tree-3d {
  position: relative;
  width: 100%;
  height: 100%;
  overflow: hidden;
  background: transparent;
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
