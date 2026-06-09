/**
 * 3D World Tree builder — holographic/digital cyber tree with data crystals,
 * hexagonal grid floor, data rings, data particles
 */
import * as THREE from 'three'
import type { PageInfo, HitArea } from './types'
import { createRng } from './canvasUtils'
import type { TreeMaterials } from './tree3dMaterials'

// ---- Types ----

interface BranchDef {
  depth: number
  index: number
  children: BranchDef[]
  page: PageInfo | null
  length: number
  angle: number    // radians from vertical, 0 = up
  twist: number    // rotation around Y axis
  thickness: number
  branchId: number
}

export interface BuildResult {
  group: THREE.Group
  dollMeshes: THREE.Object3D[]
  dollData: HitArea[]
  grassUniforms: { uTime: { value: number }; uGrowth: { value: number } }
}

// Minimum distance between crystal centers to prevent overlap
const MIN_CRYSTAL_DISTANCE = 2.5

// ---- Build ----

export function buildTree3D(
  rng: () => number,
  pages: PageInfo[],
  mats: TreeMaterials,
): BuildResult {
  const group = new THREE.Group()
  const dollMeshes: THREE.Object3D[] = []
  const dollData: HitArea[] = []
  let branchIdCounter = 0

  // Shuffle pages
  const shuffledPages = [...pages]
  for (let i = shuffledPages.length - 1; i > 0; i--) {
    const j = Math.floor(rng() * (i + 1))
    ;[shuffledPages[i], shuffledPages[j]] = [shuffledPages[j], shuffledPages[i]]
  }

  // Generate branch structure
  const l1Count = 3 + Math.floor(rng() * 3) // 3-5
  const branches: BranchDef[] = []
  for (let i = 0; i < l1Count; i++) {
    branches.push(makeBranch(rng, 1, l1Count, () => branchIdCounter++))
  }

  // Assign pages to leaf branches
  const leaves: BranchDef[] = []
  collectLeaves(branches, leaves)
  const shuffledLeaves = [...leaves]
  for (let i = shuffledLeaves.length - 1; i > 0; i--) {
    const j = Math.floor(rng() * (i + 1))
    ;[shuffledLeaves[i], shuffledLeaves[j]] = [shuffledLeaves[j], shuffledLeaves[i]]
  }
  for (let i = 0; i < Math.min(shuffledPages.length, shuffledLeaves.length); i++) {
    shuffledLeaves[i].page = shuffledPages[i]
  }

  // ---- Hexagonal Grid Floor ----
  const groundMesh = createHexGrid(mats)
  groundMesh.userData.growthOrder = 0
  group.add(groundMesh)

  // ---- Holographic Grid Particles (replaces grass) ----
  const gridParticles = createGridParticles(mats, rng)
  gridParticles.userData.growthOrder = 0
  group.add(gridParticles)
  const grassUniforms = (gridParticles as any).material.uniforms as {
    uTime: { value: number }
    uGrowth: { value: number }
  }

  // ---- Energy Roots ----
  const rootMeshes = createEnergyRoots(rng, mats)
  for (const rm of rootMeshes) {
    rm.userData.growthOrder = 0.05
    group.add(rm)
  }

  // ---- Holographic Trunk ----
  const trunk = createHolographicTrunk(mats)
  trunk.userData.growthOrder = 0
  group.add(trunk)

  // ---- Branches + Data Crystals (recursive) ----
  const trunkTop = new THREE.Vector3(0, 8, 0)
  const dollGroups: THREE.Group[] = []
  for (const b of branches) {
    buildBranch3D(group, b, trunkTop, rng, mats, dollMeshes, dollData, dollGroups, 0.1, 1)
  }

  // ---- Push apart overlapping crystals ----
  spreadDolls(dollGroups, MIN_CRYSTAL_DISTANCE)

  // ---- Data Particles (replaces fireflies) ----
  const dataParticles = createDataParticles(rng)
  dataParticles.userData.growthOrder = 0.8
  group.add(dataParticles)

  return { group, dollMeshes, dollData, grassUniforms }
}

// ---- Branch structure generation ----

function makeBranch(rng: () => number, depth: number, siblingCount: number, nextId: () => number): BranchDef {
  const childCount = depth < 3 ? (2 + Math.floor(rng() * 3)) : 0
  const spreadRange = Math.PI * (0.3 + 0.1 * siblingCount)
  const branch: BranchDef = {
    depth,
    index: 0, // will be set by parent
    children: [],
    page: null,
    length: 0,
    angle: 0,
    twist: 0,
    thickness: 0,
    branchId: nextId(),
  }

  for (let i = 0; i < childCount; i++) {
    const child = makeBranch(rng, depth + 1, childCount, nextId)
    child.index = i
    child.angle = -spreadRange / 2 + (i / (childCount - 1 || 1)) * spreadRange + (rng() - 0.5) * 0.1
    child.twist = rng() * Math.PI * 2
    child.length = (3.5 - depth * 0.6) * (0.7 + rng() * 0.3)
    child.thickness = Math.max(0.08, 0.5 - depth * 0.1 + rng() * 0.1)
    branch.children.push(child)
  }

  return branch
}

function collectLeaves(branches: BranchDef[], out: BranchDef[]): void {
  for (const b of branches) {
    if (b.children.length === 0) out.push(b)
    else collectLeaves(b.children, out)
  }
}

// ---- Spread overlapping crystals ----

function spreadDolls(dollGroups: THREE.Group[], minDist: number): void {
  // Iterative repulsion: push crystals apart if too close
  const iterations = 10
  for (let iter = 0; iter < iterations; iter++) {
    let moved = false
    for (let i = 0; i < dollGroups.length; i++) {
      for (let j = i + 1; j < dollGroups.length; j++) {
        const pi = dollGroups[i].position
        const pj = dollGroups[j].position
        const dx = pj.x - pi.x
        const dz = pj.z - pi.z
        const distXZ = Math.sqrt(dx * dx + dz * dz)
        if (distXZ < minDist && distXZ > 0.001) {
          const push = (minDist - distXZ) / 2
          const nx = dx / distXZ
          const nz = dz / distXZ
          pi.x -= nx * push
          pi.z -= nz * push
          pj.x += nx * push
          pj.z += nz * push
          moved = true
        }
      }
    }
    if (!moved) break
  }
}

// ---- 3D Branch builder (energy beams) ----

function buildBranch3D(
  parent: THREE.Group,
  branch: BranchDef,
  origin: THREE.Vector3,
  rng: () => number,
  mats: TreeMaterials,
  dollMeshes: THREE.Object3D[],
  dollData: HitArea[],
  dollGroups: THREE.Group[],
  baseGrowth: number,
  parentThickness: number,
): void {
  if (branch.children.length === 0 && branch.depth === 0) return

  // For level-1 branches from trunk top
  if (branch.depth === 1) {
    const l1Count = 5
    const spreadAngle = -Math.PI / 2.5 + (branch.index / l1Count) * (Math.PI / 1.25) + (rng() - 0.5) * 0.1
    const twistAngle = (branch.index / l1Count) * Math.PI * 2 + rng() * 0.2
    branch.angle = spreadAngle
    branch.twist = twistAngle
    branch.length = (4.0 - branch.depth * 0.4) * (0.7 + rng() * 0.3)
    branch.thickness = Math.max(0.12, 0.4 - branch.depth * 0.08 + rng() * 0.08)
  }

  const len = branch.length || 3
  const thick = branch.thickness || 0.3

  // Compute end point
  const dir = new THREE.Vector3(
    Math.sin(branch.angle) * Math.cos(branch.twist),
    Math.cos(branch.angle),
    Math.sin(branch.angle) * Math.sin(branch.twist),
  ).normalize()

  const end = origin.clone().add(dir.clone().multiplyScalar(len))
  const mid = origin.clone().lerp(end, 0.5).add(new THREE.Vector3((rng() - 0.5) * 0.5, 0.3, (rng() - 0.5) * 0.5))

  // Create energy beam branch — thin glowing line with bloom effect
  const curve = new THREE.QuadraticBezierCurve3(origin, mid, end)

  // Core beam (thin cylinder, bright cyan)
  const coreGeo = new THREE.TubeGeometry(curve, 8, thick * 0.3, 6, false)
  const coreMat = new THREE.MeshStandardMaterial({
    color: 0x00d4ff,
    emissive: 0x00d4ff,
    emissiveIntensity: 1.5,
    transparent: true,
    opacity: 0.95,
    roughness: 0.1,
    metalness: 0.9,
  })
  const coreMesh = new THREE.Mesh(coreGeo, coreMat)
  coreMesh.userData.growthOrder = baseGrowth + branch.depth * 0.08
  parent.add(coreMesh)

  // Glow shell (wider cylinder, dimmer, for bloom look)
  const glowGeo = new THREE.TubeGeometry(curve, 8, thick * 0.7, 6, false)
  const glowMat = new THREE.MeshStandardMaterial({
    color: 0x00d4ff,
    emissive: 0x00d4ff,
    emissiveIntensity: 0.4,
    transparent: true,
    opacity: 0.15,
    roughness: 0.3,
    metalness: 0.5,
    side: THREE.DoubleSide,
  })
  const glowMesh = new THREE.Mesh(glowGeo, glowMat)
  glowMesh.userData.growthOrder = baseGrowth + branch.depth * 0.08
  parent.add(glowMesh)

  // Leaf node → Data Crystal
  if (branch.children.length === 0) {
    const crystal = createDataCrystal(end, branch, rng, mats, !!branch.page)
    crystal.userData.growthOrder = baseGrowth + branch.depth * 0.08 + 0.15
    dollGroups.push(crystal)
    parent.add(crystal)

    if (branch.page) {
      const prismMesh = crystal.getObjectByName('crystalPrism')
      if (prismMesh) {
        dollMeshes.push(prismMesh)
        dollData.push({
          x: 0, y: 0, radius: 0,
          label: branch.page.label,
          desc: branch.page.desc,
          route: branch.page.route,
        })
      }
    }
    return
  }

  // Recurse into children
  for (const child of branch.children) {
    buildBranch3D(parent, child, end, rng, mats, dollMeshes, dollData, dollGroups, baseGrowth + 0.08, thick)
  }
}

// ---- Data Crystal (3D) — replaces teru-teru-bozu ----

function createDataCrystal(
  pos: THREE.Vector3,
  branch: BranchDef,
  rng: () => number,
  mats: TreeMaterials,
  hasPage: boolean,
): THREE.Group {
  const crystal = new THREE.Group()
  crystal.position.copy(pos)

  const sz = 0.4 + rng() * 0.15

  // Floating offset — crystal hovers above branch tip
  crystal.position.y += sz * 2

  // Hover connection beam (thin line from branch to crystal)
  const beamGeo = new THREE.CylinderGeometry(0.02, 0.02, sz * 2, 4)
  const beamMat = new THREE.MeshStandardMaterial({
    color: 0x00d4ff,
    emissive: 0x00d4ff,
    emissiveIntensity: 0.6,
    transparent: true,
    opacity: 0.4,
  })
  const beamMesh = new THREE.Mesh(beamGeo, beamMat)
  beamMesh.position.y = -sz * 1
  crystal.add(beamMesh)

  // Main hexagonal prism crystal
  const prismGeo = new THREE.CylinderGeometry(sz * 0.6, sz * 0.6, sz * 1.8, 6) // 6-sided = hexagonal
  const prismMat = new THREE.MeshStandardMaterial({
    color: hasPage ? 0x00d4ff : 0x1a3355,
    emissive: 0x00d4ff,
    emissiveIntensity: hasPage ? 0.6 : 0.15,
    transparent: true,
    opacity: 0.85,
    roughness: 0.05,
    metalness: 0.95,
    envMapIntensity: 2.0,
  })
  const prismMesh = new THREE.Mesh(prismGeo, prismMat)
  prismMesh.name = 'crystalPrism'
  crystal.add(prismMesh)

  // Inner glow core
  const innerGeo = new THREE.CylinderGeometry(sz * 0.3, sz * 0.3, sz * 1.6, 6)
  const innerMat = new THREE.MeshStandardMaterial({
    color: 0x00ffff,
    emissive: 0x00ffff,
    emissiveIntensity: 2.0,
    transparent: true,
    opacity: 0.3,
  })
  const innerMesh = new THREE.Mesh(innerGeo, innerMat)
  crystal.add(innerMesh)

  // Top pyramid cap
  const topCapGeo = new THREE.ConeGeometry(sz * 0.6, sz * 0.6, 6)
  const topCapMat = new THREE.MeshStandardMaterial({
    color: 0x00d4ff,
    emissive: 0x00d4ff,
    emissiveIntensity: 0.8,
    transparent: true,
    opacity: 0.7,
    roughness: 0.1,
    metalness: 0.9,
  })
  const topCap = new THREE.Mesh(topCapGeo, topCapMat)
  topCap.position.y = sz * 1.2
  crystal.add(topCap)

  // Bottom pyramid cap
  const botCapGeo = new THREE.ConeGeometry(sz * 0.6, sz * 0.4, 6)
  const botCap = new THREE.Mesh(botCapGeo, topCapMat.clone())
  botCap.rotation.x = Math.PI
  botCap.position.y = -sz * 1.1
  crystal.add(botCap)

  // ---- Data Rings (replaces spirit rings) — only for real pages ----
  if (hasPage) {
    const ringRng = createRng(branch.branchId * 37 + 42)
    const ringCount = 1 + Math.floor(ringRng() * 3)

    for (let i = 0; i < ringCount; i++) {
      const ringRadius = sz * (1.0 + ringRng() * 1.0)
      const ringTubeRadius = 0.015 + ringRng() * 0.01

      // Thin tech ring with dashed look
      const ringGeo = new THREE.TorusGeometry(ringRadius, ringTubeRadius, 6, 48)
      const ringMat = new THREE.MeshStandardMaterial({
        color: i % 2 === 0 ? 0x00d4ff : 0xff00ff,
        emissive: i % 2 === 0 ? 0x00d4ff : 0xff00ff,
        emissiveIntensity: 0.8,
        transparent: true,
        opacity: 0.6,
        roughness: 0.2,
        metalness: 0.8,
      })

      const ringMesh = new THREE.Mesh(ringGeo, ringMat)
      ringMesh.position.y = (ringRng() - 0.5) * sz * 0.8
      ringMesh.rotation.x = Math.PI / 2 + (ringRng() - 0.5) * 0.8
      ringMesh.rotation.z = ringRng() * Math.PI
      ringMesh.userData.spinSpeed = 0.3 + ringRng() * 0.5
      ringMesh.userData.spinAxis = new THREE.Vector3(
        ringRng() - 0.5, 1, ringRng() - 0.5
      ).normalize()
      ringMesh.name = 'spiritRing' // keep same name for animator compatibility
      crystal.add(ringMesh)

      // Add dashed ring effect — thin line ring overlapping the torus
      if (i === 0) {
        const dashRingPoints: THREE.Vector3[] = []
        const dashSegs = 48
        for (let d = 0; d < dashSegs; d++) {
          // Skip every other segment for dashed look
          if (d % 3 === 2) continue
          const angle = (d / dashSegs) * Math.PI * 2
          const nextAngle = ((d + 1) / dashSegs) * Math.PI * 2
          dashRingPoints.push(new THREE.Vector3(Math.cos(angle) * ringRadius, 0, Math.sin(angle) * ringRadius))
          dashRingPoints.push(new THREE.Vector3(Math.cos(nextAngle) * ringRadius, 0, Math.sin(nextAngle) * ringRadius))
        }
        const dashGeo = new THREE.BufferGeometry().setFromPoints(dashRingPoints)
        const dashMat = new THREE.LineBasicMaterial({
          color: 0x00d4ff,
          transparent: true,
          opacity: 0.4,
        })
        const dashLine = new THREE.LineSegments(dashGeo, dashMat)
        dashLine.rotation.x = ringMesh.rotation.x
        dashLine.rotation.z = ringMesh.rotation.z
        dashLine.position.y = ringMesh.position.y
        crystal.add(dashLine)
      }
    }
  }

  // Add animation data
  crystal.userData.swayFreq = 0.8 + (branch.branchId % 5) * 0.15
  crystal.userData.swayPhase = branch.branchId * 2.3
  crystal.userData.isDoll = true
  crystal.userData.floatPhase = rng() * Math.PI * 2

  return crystal
}

// ---- Hexagonal Grid Floor (replaces ground) ----

function createHexGrid(mats: TreeMaterials): THREE.Group {
  const gridGroup = new THREE.Group()
  const hexRadius = 1.2
  const hexHeight = hexRadius * Math.sqrt(3)
  const gridRadius = 12

  // Center hex
  const centerGeo = new THREE.CircleGeometry(hexRadius * 0.95, 6)
  centerGeo.rotateX(-Math.PI / 2)
  const centerMat = new THREE.MeshStandardMaterial({
    color: 0x00d4ff,
    emissive: 0x00d4ff,
    emissiveIntensity: 0.15,
    transparent: true,
    opacity: 0.12,
    roughness: 0.3,
    metalness: 0.8,
    side: THREE.DoubleSide,
  })
  const centerMesh = new THREE.Mesh(centerGeo, centerMat)
  centerMesh.position.y = -0.05
  gridGroup.add(centerMesh)

  // Hex grid — axial coordinate system
  const hexPoints: THREE.Vector3[] = []
  const qMax = Math.ceil(gridRadius / (hexRadius * 1.5))

  for (let q = -qMax; q <= qMax; q++) {
    for (let r = -qMax; r <= qMax; r++) {
      const x = hexRadius * 1.5 * q
      const z = hexHeight * (r + q * 0.5)
      const dist = Math.sqrt(x * x + z * z)
      if (dist > gridRadius) continue

      // Wireframe hexagon
      const verts: THREE.Vector3[] = []
      for (let i = 0; i < 6; i++) {
        const angle = Math.PI / 3 * i + Math.PI / 6
        const nextAngle = Math.PI / 3 * (i + 1) + Math.PI / 6
        verts.push(
          new THREE.Vector3(x + Math.cos(angle) * hexRadius * 0.95, 0, z + Math.sin(angle) * hexRadius * 0.95),
          new THREE.Vector3(x + Math.cos(nextAngle) * hexRadius * 0.95, 0, z + Math.sin(nextAngle) * hexRadius * 0.95),
        )
      }

      hexPoints.push(...verts)

      // Faint filled hex
      const distFade = 1 - (dist / gridRadius)
      if (distFade > 0.1) {
        const fillGeo = new THREE.CircleGeometry(hexRadius * 0.92, 6)
        fillGeo.rotateX(-Math.PI / 2)
        const fillMat = new THREE.MeshStandardMaterial({
          color: 0x00d4ff,
          emissive: 0x00d4ff,
          emissiveIntensity: 0.05,
          transparent: true,
          opacity: 0.03 * distFade,
          roughness: 0.5,
          metalness: 0.5,
          side: THREE.DoubleSide,
        })
        const fillMesh = new THREE.Mesh(fillGeo, fillMat)
        fillMesh.position.set(x, -0.06, z)
        gridGroup.add(fillMesh)
      }
    }
  }

  // Wireframe lines
  const wireGeo = new THREE.BufferGeometry().setFromPoints(hexPoints)
  const wireMat = new THREE.LineBasicMaterial({
    color: 0x00d4ff,
    transparent: true,
    opacity: 0.2,
  })
  const wireLines = new THREE.LineSegments(wireGeo, wireMat)
  wireLines.position.y = -0.04
  gridGroup.add(wireLines)

  // Central glow disc
  const glowGeo = new THREE.CircleGeometry(5, 48)
  glowGeo.rotateX(-Math.PI / 2)
  const glowMat = new THREE.MeshStandardMaterial({
    color: 0x00d4ff,
    emissive: 0x00d4ff,
    emissiveIntensity: 0.3,
    transparent: true,
    opacity: 0.08,
    side: THREE.DoubleSide,
  })
  const glowMesh = new THREE.Mesh(glowGeo, glowMat)
  glowMesh.position.y = -0.07
  gridGroup.add(glowMesh)

  return gridGroup
}

// ---- Grid Particles (replaces grass) ----

function createGridParticles(mats: TreeMaterials, rng: () => number): THREE.Points {
  const count = 2000
  const positions = new Float32Array(count * 3)
  const sizes = new Float32Array(count)
  const phases = new Float32Array(count)

  for (let i = 0; i < count; i++) {
    const angle = rng() * Math.PI * 2
    const radius = 0.5 + rng() * 18
    positions[i * 3] = Math.cos(angle) * radius
    positions[i * 3 + 1] = rng() * 0.3  // near ground
    positions[i * 3 + 2] = Math.sin(angle) * radius
    sizes[i] = 0.05 + rng() * 0.1
    phases[i] = rng() * Math.PI * 2
  }

  const geo = new THREE.BufferGeometry()
  geo.setAttribute('position', new THREE.BufferAttribute(positions, 3))
  geo.setAttribute('aSize', new THREE.BufferAttribute(sizes, 1))
  geo.setAttribute('aPhase', new THREE.BufferAttribute(phases, 1))

  const mat = new THREE.ShaderMaterial({
    uniforms: {
      uTime: { value: 0 },
      uGrowth: { value: 0 },
      uPixelRatio: { value: Math.min(window.devicePixelRatio, 2) },
    },
    vertexShader: `
      attribute float aSize;
      attribute float aPhase;
      uniform float uTime;
      uniform float uGrowth;
      uniform float uPixelRatio;
      varying float vAlpha;

      void main() {
        vec3 pos = position;
        pos.y += sin(uTime * 0.5 + aPhase) * 0.15 * uGrowth;
        pos *= uGrowth;

        vec4 mvPos = modelViewMatrix * vec4(pos, 1.0);
        float pulse = 0.3 + 0.7 * (0.5 + 0.5 * sin(uTime * 2.0 + aPhase));
        vAlpha = pulse * uGrowth;
        gl_PointSize = aSize * uPixelRatio * (200.0 / -mvPos.z) * pulse;
        gl_Position = projectionMatrix * mvPos;
      }
    `,
    fragmentShader: `
      varying float vAlpha;

      void main() {
        float d = length(gl_PointCoord - 0.5) * 2.0;
        if (d > 1.0) discard;
        float glow = 1.0 - d * d;
        gl_FragColor = vec4(0.0, 0.83, 1.0, vAlpha * glow * 0.5);
      }
    `,
    transparent: true,
    depthWrite: false,
    blending: THREE.AdditiveBlending,
  })

  const points = new THREE.Points(geo, mat)
  return points
}

// ---- Energy Roots (replaces organic roots) ----

function createEnergyRoots(rng: () => number, mats: TreeMaterials): THREE.Mesh[] {
  const rootDefs = [
    { angle: -0.6, len: 3, thick: 0.15 },
    { angle: -0.3, len: 2.2, thick: 0.1 },
    { angle: 0.2, len: 2.5, thick: 0.12 },
    { angle: 0.5, len: 2.8, thick: 0.13 },
    { angle: -0.85, len: 1.8, thick: 0.08 },
    { angle: 0.75, len: 2.0, thick: 0.09 },
  ]

  return rootDefs.map((r) => {
    const start = new THREE.Vector3(r.angle * 1.5, 0, (rng() - 0.5) * 1.5)
    const end = new THREE.Vector3(
      start.x + Math.cos(r.angle) * r.len,
      -0.3 - rng() * 0.3,
      start.z + Math.sin(r.angle) * r.len * 0.3,
    )
    const mid = start.clone().lerp(end, 0.5).add(new THREE.Vector3((rng() - 0.5) * 0.5, -0.2, (rng() - 0.5) * 0.3))

    const curve = new THREE.QuadraticBezierCurve3(start, mid, end)

    // Core energy line
    const coreGeo = new THREE.TubeGeometry(curve, 8, Math.max(0.03, r.thick * 0.5), 4, false)
    const coreMat = new THREE.MeshStandardMaterial({
      color: 0x00d4ff,
      emissive: 0x00d4ff,
      emissiveIntensity: 1.2,
      transparent: true,
      opacity: 0.8,
      roughness: 0.1,
      metalness: 0.9,
    })
    return new THREE.Mesh(coreGeo, coreMat)
  })
}

// ---- Holographic Trunk (replaces organic trunk) ----

function createHolographicTrunk(mats: TreeMaterials): THREE.Group {
  const trunkGroup = new THREE.Group()

  // Main trunk — glowing segmented pillar
  const trunkGeo = new THREE.CylinderGeometry(0.3, 0.8, 8, 8, 8, false)

  // Displace vertices for slight irregularity
  const pos = trunkGeo.attributes.position
  const rng = createRng(5678)
  for (let i = 0; i < pos.count; i++) {
    const x = pos.getX(i), y = pos.getY(i), z = pos.getZ(i)
    const dist = Math.sqrt(x * x + z * z)
    if (dist > 0.1) {
      const angle = Math.atan2(z, x)
      const noise = (rng() - 0.5) * 0.08 * (dist / 0.8)
      pos.setX(i, x + Math.cos(angle) * noise)
      pos.setZ(i, z + Math.sin(angle) * noise)
    }
  }
  pos.needsUpdate = true
  trunkGeo.computeVertexNormals()

  // Core trunk mesh — bright cyan holographic
  const trunkMat = new THREE.MeshStandardMaterial({
    color: 0x00d4ff,
    emissive: 0x00d4ff,
    emissiveIntensity: 1.0,
    transparent: true,
    opacity: 0.85,
    roughness: 0.05,
    metalness: 0.95,
  })
  const trunkMesh = new THREE.Mesh(trunkGeo, trunkMat)
  trunkMesh.position.y = 4
  trunkGroup.add(trunkMesh)

  // Outer glow shell
  const glowGeo = new THREE.CylinderGeometry(0.5, 1.0, 8, 8, 8, false)
  const glowMat = new THREE.MeshStandardMaterial({
    color: 0x00d4ff,
    emissive: 0x00d4ff,
    emissiveIntensity: 0.3,
    transparent: true,
    opacity: 0.1,
    side: THREE.DoubleSide,
    roughness: 0.3,
    metalness: 0.5,
  })
  const glowMesh = new THREE.Mesh(glowGeo, glowMat)
  glowMesh.position.y = 4
  trunkGroup.add(glowMesh)

  // Horizontal ring segments along trunk (tech detail)
  const ringCount = 6
  for (let i = 0; i < ringCount; i++) {
    const y = 1 + i * (6 / ringCount)
    const yRatio = y / 8
    const radius = 0.8 - yRatio * 0.5
    const ringGeo = new THREE.TorusGeometry(Math.max(0.1, radius), 0.02, 6, 24)
    const ringMat = new THREE.MeshStandardMaterial({
      color: i % 2 === 0 ? 0x00d4ff : 0xff00ff,
      emissive: i % 2 === 0 ? 0x00d4ff : 0xff00ff,
      emissiveIntensity: 0.6,
      transparent: true,
      opacity: 0.5,
    })
    const ringMesh = new THREE.Mesh(ringGeo, ringMat)
    ringMesh.rotation.x = Math.PI / 2
    ringMesh.position.y = y
    trunkGroup.add(ringMesh)
  }

  // Vertical line details on trunk surface
  const lineCount = 8
  for (let i = 0; i < lineCount; i++) {
    const angle = (i / lineCount) * Math.PI * 2
    const topR = 0.31
    const botR = 0.81
    const points = [
      new THREE.Vector3(Math.cos(angle) * botR, 0, Math.sin(angle) * botR),
      new THREE.Vector3(Math.cos(angle) * topR, 8, Math.sin(angle) * topR),
    ]
    const lineGeo = new THREE.BufferGeometry().setFromPoints(points)
    const lineMat = new THREE.LineBasicMaterial({
      color: 0x00d4ff,
      transparent: true,
      opacity: 0.4,
    })
    const line = new THREE.Line(lineGeo, lineMat)
    trunkGroup.add(line)
  }

  return trunkGroup
}

// ---- Data Particles (replaces fireflies) ----

function createDataParticles(rng: () => number): THREE.Points {
  const count = 80
  const positions = new Float32Array(count * 3)
  const sizes = new Float32Array(count)
  const phases = new Float32Array(count)

  for (let i = 0; i < count; i++) {
    positions[i * 3] = (rng() - 0.5) * 24
    positions[i * 3 + 1] = 2 + rng() * 14
    positions[i * 3 + 2] = (rng() - 0.5) * 24
    sizes[i] = 0.08 + rng() * 0.18
    phases[i] = rng() * Math.PI * 2
  }

  const geo = new THREE.BufferGeometry()
  geo.setAttribute('position', new THREE.BufferAttribute(positions, 3))
  geo.setAttribute('aSize', new THREE.BufferAttribute(sizes, 1))
  geo.setAttribute('aPhase', new THREE.BufferAttribute(phases, 1))

  const mat = new THREE.ShaderMaterial({
    uniforms: {
      uTime: { value: 0 },
      uPixelRatio: { value: Math.min(window.devicePixelRatio, 2) },
    },
    vertexShader: `
      attribute float aSize;
      attribute float aPhase;
      uniform float uTime;
      uniform float uPixelRatio;
      varying float vAlpha;
      varying float vPhase;

      void main() {
        vec3 pos = position;
        // Slow drift
        pos.x += sin(uTime * 0.3 + aPhase) * 0.5;
        pos.y += sin(uTime * 0.5 + aPhase * 1.3) * 0.3;
        pos.z += cos(uTime * 0.4 + aPhase * 0.7) * 0.5;

        vec4 mvPos = modelViewMatrix * vec4(pos, 1.0);
        float pulse = 0.3 + 0.7 * (0.5 + 0.5 * sin(uTime * 1.2 + aPhase));
        vAlpha = pulse;
        vPhase = aPhase;
        gl_PointSize = aSize * uPixelRatio * (200.0 / -mvPos.z) * pulse;
        gl_Position = projectionMatrix * mvPos;
      }
    `,
    fragmentShader: `
      varying float vAlpha;
      varying float vPhase;

      void main() {
        // Hexagonal point shape
        vec2 p = gl_PointCoord - 0.5;
        float d = length(p) * 2.0;
        if (d > 1.0) discard;

        // Hexagonal mask approximation
        float hexDist = max(abs(p.x), abs(p.x * 0.5 + p.y * 0.866) * 1.1);
        hexDist = max(hexDist, abs(p.x * 0.5 - p.y * 0.866) * 1.1);
        if (hexDist > 0.5) discard;

        float glow = 1.0 - d * d;
        // Mix cyan and magenta based on phase
        vec3 col = mix(vec3(0.0, 0.83, 1.0), vec3(1.0, 0.0, 1.0), sin(vPhase) * 0.5 + 0.5);
        gl_FragColor = vec4(col, vAlpha * glow * 0.7);
      }
    `,
    transparent: true,
    depthWrite: false,
    blending: THREE.AdditiveBlending,
  })

  const points = new THREE.Points(geo, mat)
  points.userData.fireflyMat = mat  // keep same key for animator compatibility
  return points
}
