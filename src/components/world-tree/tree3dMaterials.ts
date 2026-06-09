/**
 * 3D Tree materials — procedural bark texture, cloth, ground, etc.
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

// ---- Procedural bark texture ----

function makeBarkTexture(width: number, height: number, baseColor: THREE.Color, darkColor: THREE.Color): THREE.CanvasTexture {
  const canvas = document.createElement('canvas')
  canvas.width = width
  canvas.height = height
  const ctx = canvas.getContext('2d')!

  // Base fill
  ctx.fillStyle = `rgb(${baseColor.r * 255 | 0}, ${baseColor.g * 255 | 0}, ${baseColor.b * 255 | 0})`
  ctx.fillRect(0, 0, width, height)

  // Bark lines — vertical streaks
  const streakCount = 40
  for (let i = 0; i < streakCount; i++) {
    const x = Math.random() * width
    const w = 1 + Math.random() * 3
    const alpha = 0.1 + Math.random() * 0.2
    ctx.strokeStyle = `rgba(${darkColor.r * 255 | 0}, ${darkColor.g * 255 | 0}, ${darkColor.b * 255 | 0}, ${alpha})`
    ctx.lineWidth = w
    ctx.beginPath()
    let y = 0
    ctx.moveTo(x, y)
    while (y < height) {
      y += 5 + Math.random() * 15
      ctx.lineTo(x + (Math.random() - 0.5) * 6, y)
    }
    ctx.stroke()
  }

  // Bark knots — horizontal cracks
  for (let i = 0; i < 15; i++) {
    const kx = Math.random() * width
    const ky = Math.random() * height
    const kw = 8 + Math.random() * 20
    const kh = 2 + Math.random() * 4
    ctx.fillStyle = `rgba(${darkColor.r * 255 | 0}, ${darkColor.g * 255 | 0}, ${darkColor.b * 255 | 0}, ${0.15 + Math.random() * 0.15})`
    ctx.beginPath()
    ctx.ellipse(kx, ky, kw, kh, Math.random() * 0.3, 0, Math.PI * 2)
    ctx.fill()
  }

  // Noise overlay
  const imgData = ctx.getImageData(0, 0, width, height)
  for (let i = 0; i < imgData.data.length; i += 4) {
    const n = (Math.random() - 0.5) * 20
    imgData.data[i] = Math.max(0, Math.min(255, imgData.data[i] + n))
    imgData.data[i + 1] = Math.max(0, Math.min(255, imgData.data[i + 1] + n))
    imgData.data[i + 2] = Math.max(0, Math.min(255, imgData.data[i + 2] + n))
  }
  ctx.putImageData(imgData, 0, 0)

  const tex = new THREE.CanvasTexture(canvas)
  tex.wrapS = tex.wrapT = THREE.RepeatWrapping
  tex.repeat.set(2, 4)
  return tex
}

// ---- Procedural ground texture ----

function makeGroundTexture(width: number, height: number): THREE.CanvasTexture {
  const canvas = document.createElement('canvas')
  canvas.width = width
  canvas.height = height
  const ctx = canvas.getContext('2d')!

  // Dark earth base
  const grad = ctx.createRadialGradient(width / 2, height / 2, 0, width / 2, height / 2, width * 0.5)
  grad.addColorStop(0, '#2d4a1e')
  grad.addColorStop(0.5, '#1a3312')
  grad.addColorStop(1, '#0d1a0a')
  ctx.fillStyle = grad
  ctx.fillRect(0, 0, width, height)

  // Scattered dark spots
  for (let i = 0; i < 200; i++) {
    const x = Math.random() * width
    const y = Math.random() * height
    const r = 2 + Math.random() * 6
    ctx.fillStyle = `rgba(0, 0, 0, ${0.05 + Math.random() * 0.1})`
    ctx.beginPath()
    ctx.arc(x, y, r, 0, Math.PI * 2)
    ctx.fill()
  }

  // Golden glow near center
  const glow = ctx.createRadialGradient(width / 2, height / 2, 0, width / 2, height / 2, width * 0.3)
  glow.addColorStop(0, 'rgba(212, 160, 23, 0.08)')
  glow.addColorStop(1, 'rgba(0, 0, 0, 0)')
  ctx.fillStyle = glow
  ctx.fillRect(0, 0, width, height)

  const tex = new THREE.CanvasTexture(canvas)
  tex.wrapS = tex.wrapT = THREE.RepeatWrapping
  return tex
}

// ---- Procedural normal map for bark ----

function makeBarkNormalMap(width: number, height: number): THREE.CanvasTexture {
  const canvas = document.createElement('canvas')
  canvas.width = width
  canvas.height = height
  const ctx = canvas.getContext('2d')!

  // Flat normal base (0.5, 0.5, 1.0)
  ctx.fillStyle = '#8080ff'
  ctx.fillRect(0, 0, width, height)

  // Bark groove normals — vertical streaks
  for (let i = 0; i < 30; i++) {
    const x = Math.random() * width
    const w = 2 + Math.random() * 4
    const strength = 20 + Math.random() * 30
    ctx.strokeStyle = `rgb(${128 - strength | 0}, ${128 | 0}, 255)`
    ctx.lineWidth = w
    ctx.beginPath()
    let y = 0
    ctx.moveTo(x, y)
    while (y < height) {
      y += 4 + Math.random() * 12
      ctx.lineTo(x + (Math.random() - 0.5) * 4, y)
    }
    ctx.stroke()
  }

  const tex = new THREE.CanvasTexture(canvas)
  tex.wrapS = tex.wrapT = THREE.RepeatWrapping
  tex.repeat.set(2, 4)
  return tex
}

// ---- Cloth texture ----

function makeClothTexture(width: number, height: number): THREE.CanvasTexture {
  const canvas = document.createElement('canvas')
  canvas.width = width
  canvas.height = height
  const ctx = canvas.getContext('2d')!

  ctx.fillStyle = '#f0ebe0'
  ctx.fillRect(0, 0, width, height)

  // Subtle weave pattern
  for (let y = 0; y < height; y += 2) {
    for (let x = 0; x < width; x += 2) {
      if ((x + y) % 4 === 0) {
        ctx.fillStyle = `rgba(200, 190, 170, 0.15)`
        ctx.fillRect(x, y, 2, 2)
      }
    }
  }

  const tex = new THREE.CanvasTexture(canvas)
  return tex
}

// ---- Create all materials ----

export function createTreeMaterials(): TreeMaterials {
  const barkBase = new THREE.Color(0x6b4423)
  const barkDark = new THREE.Color(0x3d2510)

  const trunkBarkTex = makeBarkTexture(512, 1024, barkBase, barkDark)
  const trunkBarkNormal = makeBarkNormalMap(512, 1024)
  const groundTex = makeGroundTexture(1024, 1024)
  const clothTex = makeClothTexture(128, 128)

  return {
    trunkBark: new THREE.MeshStandardMaterial({
      map: trunkBarkTex,
      normalMap: trunkBarkNormal,
      normalScale: new THREE.Vector2(0.8, 0.8),
      roughness: 0.85,
      metalness: 0.05,
      color: 0x8b6914,
    }),
    bark: new THREE.MeshStandardMaterial({
      map: trunkBarkTex,
      normalMap: trunkBarkNormal,
      normalScale: new THREE.Vector2(0.6, 0.6),
      roughness: 0.8,
      metalness: 0.05,
      color: 0x8b6914,
    }),
    rootBark: new THREE.MeshStandardMaterial({
      map: trunkBarkTex,
      normalMap: trunkBarkNormal,
      normalScale: new THREE.Vector2(0.5, 0.5),
      roughness: 0.9,
      metalness: 0.02,
      color: 0x3d2510,
    }),
    cloth: new THREE.MeshStandardMaterial({
      map: clothTex,
      roughness: 0.95,
      metalness: 0.0,
      color: 0xf0ebe0,
    }),
    string: new THREE.MeshStandardMaterial({
      color: 0xc8b48c,
      roughness: 0.9,
      metalness: 0.0,
    }),
    ground: new THREE.MeshStandardMaterial({
      map: groundTex,
      roughness: 0.95,
      metalness: 0.0,
      color: 0x1a3312,
    }),
  }
}
