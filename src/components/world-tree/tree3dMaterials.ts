/**
 * 3D Tree materials — holographic/cyber sci-fi materials
 */
import * as THREE from 'three'

export interface TreeMaterials {
  trunkBark: THREE.MeshStandardMaterial
  bark: THREE.MeshStandardMaterial
  rootBark: THREE.MeshStandardMaterial
  cloth: THREE.MeshStandardMaterial
  string: THREE.MeshStandardMaterial
  ground: THREE.MeshStandardMaterial
}

// ---- Procedural holographic texture ----

function makeHoloTexture(width: number, height: number): THREE.CanvasTexture {
  const canvas = document.createElement('canvas')
  canvas.width = width
  canvas.height = height
  const ctx = canvas.getContext('2d')!

  // Dark base with subtle blue tint
  ctx.fillStyle = '#050a1a'
  ctx.fillRect(0, 0, width, height)

  // Scan lines
  for (let y = 0; y < height; y += 3) {
    ctx.fillStyle = `rgba(0, 212, 255, ${0.02 + Math.random() * 0.03})`
    ctx.fillRect(0, y, width, 1)
  }

  // Grid pattern overlay
  ctx.strokeStyle = 'rgba(0, 212, 255, 0.04)'
  ctx.lineWidth = 0.5
  const gridSize = 20
  for (let x = 0; x < width; x += gridSize) {
    ctx.beginPath()
    ctx.moveTo(x, 0)
    ctx.lineTo(x, height)
    ctx.stroke()
  }
  for (let y = 0; y < height; y += gridSize) {
    ctx.beginPath()
    ctx.moveTo(0, y)
    ctx.lineTo(width, y)
    ctx.stroke()
  }

  // Bright glitch streaks
  for (let i = 0; i < 15; i++) {
    const y = Math.random() * height
    const h = 1 + Math.random() * 2
    ctx.fillStyle = `rgba(0, 212, 255, ${0.05 + Math.random() * 0.1})`
    ctx.fillRect(0, y, width, h)
  }

  // Noise
  const imgData = ctx.getImageData(0, 0, width, height)
  for (let i = 0; i < imgData.data.length; i += 4) {
    const n = (Math.random() - 0.5) * 10
    imgData.data[i] = Math.max(0, Math.min(255, imgData.data[i] + n))
    imgData.data[i + 1] = Math.max(0, Math.min(255, imgData.data[i + 1] + n))
    imgData.data[i + 2] = Math.max(0, Math.min(255, imgData.data[i + 2] + n + 5))
  }
  ctx.putImageData(imgData, 0, 0)

  const tex = new THREE.CanvasTexture(canvas)
  tex.wrapS = tex.wrapT = THREE.RepeatWrapping
  tex.repeat.set(2, 4)
  return tex
}

// ---- Procedural hex grid ground texture ----

function makeHexGroundTexture(width: number, height: number): THREE.CanvasTexture {
  const canvas = document.createElement('canvas')
  canvas.width = width
  canvas.height = height
  const ctx = canvas.getContext('2d')!

  // Deep space navy base
  const grad = ctx.createRadialGradient(width / 2, height / 2, 0, width / 2, height / 2, width * 0.5)
  grad.addColorStop(0, '#0a1028')
  grad.addColorStop(0.5, '#060c1e')
  grad.addColorStop(1, '#030610')
  ctx.fillStyle = grad
  ctx.fillRect(0, 0, width, height)

  // Hex grid lines
  const hexSize = 30
  ctx.strokeStyle = 'rgba(0, 212, 255, 0.08)'
  ctx.lineWidth = 0.5

  for (let row = 0; row < height / (hexSize * 1.5) + 1; row++) {
    for (let col = 0; col < width / (hexSize * Math.sqrt(3)) + 1; col++) {
      const x = col * hexSize * Math.sqrt(3) + (row % 2) * hexSize * Math.sqrt(3) / 2
      const y = row * hexSize * 1.5
      ctx.beginPath()
      for (let i = 0; i < 6; i++) {
        const angle = Math.PI / 3 * i + Math.PI / 6
        const px = x + Math.cos(angle) * hexSize
        const py = y + Math.sin(angle) * hexSize
        if (i === 0) ctx.moveTo(px, py)
        else ctx.lineTo(px, py)
      }
      ctx.closePath()
      ctx.stroke()
    }
  }

  // Central cyan glow
  const glow = ctx.createRadialGradient(width / 2, height / 2, 0, width / 2, height / 2, width * 0.3)
  glow.addColorStop(0, 'rgba(0, 212, 255, 0.06)')
  glow.addColorStop(1, 'rgba(0, 0, 0, 0)')
  ctx.fillStyle = glow
  ctx.fillRect(0, 0, width, height)

  const tex = new THREE.CanvasTexture(canvas)
  tex.wrapS = tex.wrapT = THREE.RepeatWrapping
  return tex
}

// ---- Procedural crystal texture ----

function makeCrystalTexture(width: number, height: number): THREE.CanvasTexture {
  const canvas = document.createElement('canvas')
  canvas.width = width
  canvas.height = height
  const ctx = canvas.getContext('2d')!

  // Dark base with holographic shimmer
  ctx.fillStyle = '#0a1a2e'
  ctx.fillRect(0, 0, width, height)

  // Diagonal holographic lines
  ctx.strokeStyle = 'rgba(0, 212, 255, 0.15)'
  ctx.lineWidth = 0.5
  for (let i = -height; i < width + height; i += 8) {
    ctx.beginPath()
    ctx.moveTo(i, 0)
    ctx.lineTo(i - height, height)
    ctx.stroke()
  }

  // Bright spots
  for (let i = 0; i < 20; i++) {
    const x = Math.random() * width
    const y = Math.random() * height
    const r = 1 + Math.random() * 3
    const grad2 = ctx.createRadialGradient(x, y, 0, x, y, r)
    grad2.addColorStop(0, 'rgba(0, 255, 255, 0.3)')
    grad2.addColorStop(1, 'rgba(0, 212, 255, 0)')
    ctx.fillStyle = grad2
    ctx.beginPath()
    ctx.arc(x, y, r, 0, Math.PI * 2)
    ctx.fill()
  }

  const tex = new THREE.CanvasTexture(canvas)
  tex.wrapS = tex.wrapT = THREE.RepeatWrapping
  return tex
}

// ---- Create all materials (cyber/sci-fi) ----

export function createTreeMaterials(): TreeMaterials {
  const holoTex = makeHoloTexture(512, 1024)
  const groundTex = makeHexGroundTexture(1024, 1024)
  const crystalTex = makeCrystalTexture(128, 128)

  return {
    trunkBark: new THREE.MeshStandardMaterial({
      map: holoTex,
      color: 0x00d4ff,
      emissive: 0x00d4ff,
      emissiveIntensity: 1.0,
      transparent: true,
      opacity: 0.85,
      roughness: 0.05,
      metalness: 0.95,
    }),
    bark: new THREE.MeshStandardMaterial({
      map: holoTex,
      color: 0x00d4ff,
      emissive: 0x00d4ff,
      emissiveIntensity: 0.8,
      transparent: true,
      opacity: 0.9,
      roughness: 0.1,
      metalness: 0.9,
    }),
    rootBark: new THREE.MeshStandardMaterial({
      map: holoTex,
      color: 0x00d4ff,
      emissive: 0x00d4ff,
      emissiveIntensity: 1.2,
      transparent: true,
      opacity: 0.8,
      roughness: 0.1,
      metalness: 0.9,
    }),
    cloth: new THREE.MeshStandardMaterial({
      map: crystalTex,
      color: 0x00d4ff,
      emissive: 0x00d4ff,
      emissiveIntensity: 0.6,
      transparent: true,
      opacity: 0.85,
      roughness: 0.05,
      metalness: 0.95,
    }),
    string: new THREE.MeshStandardMaterial({
      color: 0x00d4ff,
      emissive: 0x00d4ff,
      emissiveIntensity: 0.6,
      transparent: true,
      opacity: 0.4,
      roughness: 0.1,
      metalness: 0.8,
    }),
    ground: new THREE.MeshStandardMaterial({
      map: groundTex,
      color: 0x060c1e,
      emissive: 0x00d4ff,
      emissiveIntensity: 0.05,
      roughness: 0.8,
      metalness: 0.3,
    }),
  }
}
