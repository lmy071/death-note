/**
 * 3D World Tree builder — procedural tree with bark texture, branches, roots,
 * teru-teru-bozu dolls, grass, ground, fireflies
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

// Minimum distance between doll centers to prevent overlap
const MIN_DOLL_DISTANCE = 2.5

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

  // ---- Ground ----
  const groundMesh = createGround(mats)
  groundMesh.userData.growthOrder = 0
  group.add(groundMesh)

  // ---- Grass ----
  const grassMesh = createGrass(mats, rng)
  grassMesh.userData.growthOrder = 0
  group.add(grassMesh)
  const grassUniforms = (grassMesh as any).material.uniforms as {
    uTime: { value: number }
    uGrowth: { value: number }
  }

  // ---- Roots ----
  const rootMeshes = createRoots(rng, mats)
  for (const rm of rootMeshes) {
    rm.userData.growthOrder = 0.05
    group.add(rm)
  }

  // ---- Trunk ----
  const trunk = createTrunk(mats)
  trunk.userData.growthOrder = 0
  group.add(trunk)

  // ---- Branches + dolls (recursive) ----
  const trunkTop = new THREE.Vector3(0, 8, 0)
  const dollGroups: THREE.Group[] = []
  for (const b of branches) {
    buildBranch3D(group, b, trunkTop, rng, mats, dollMeshes, dollData, dollGroups, 0.1, 1)
  }

  // ---- Push apart overlapping dolls ----
  spreadDolls(dollGroups, MIN_DOLL_DISTANCE)

  // ---- Fireflies ----
  const fireflies = createFireflies(rng)
  fireflies.userData.growthOrder = 0.8
  group.add(fireflies)

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

// ---- Spread overlapping dolls ----

function spreadDolls(dollGroups: THREE.Group[], minDist: number): void {
  // Iterative repulsion: push dolls apart if too close
  // Only adjust XZ (horizontal), keep Y unchanged to preserve tree structure
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

// ---- 3D Branch builder ----

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
    const l1Count = 5 // assume max 5 L1 branches
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

  // Create branch mesh using TubeGeometry along a curve
  const curve = new THREE.QuadraticBezierCurve3(origin, mid, end)
  const tubeSegs = 8
  const radSegs = 6
  const tubeGeo = new THREE.TubeGeometry(curve, tubeSegs, thick, radSegs, false)

  const depthRatio = Math.min(1, branch.depth / 4)
  const branchMat = mats.bark.clone()
  branchMat.color = new THREE.Color().lerpColors(
    new THREE.Color(0x8b6914),
    new THREE.Color(0xd4a017),
    1 - depthRatio * 0.5
  )

  const mesh = new THREE.Mesh(tubeGeo, branchMat)
  mesh.castShadow = true
  mesh.receiveShadow = true
  mesh.userData.growthOrder = baseGrowth + branch.depth * 0.08
  parent.add(mesh)

  // Leaf node → teru teru bozu
  if (branch.children.length === 0) {
    const doll = createTeruTeruBozu(end, branch, rng, mats, !!branch.page)
    doll.userData.growthOrder = baseGrowth + branch.depth * 0.08 + 0.15
    dollGroups.push(doll)
    parent.add(doll)

    if (branch.page) {
      const headSphere = doll.getObjectByName('dollHead')
      if (headSphere) {
        dollMeshes.push(headSphere)
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

// ---- Teru Teru Bozu (3D) ----

function createTeruTeruBozu(
  pos: THREE.Vector3,
  branch: BranchDef,
  rng: () => number,
  mats: TreeMaterials,
  hasPage: boolean,
): THREE.Group {
  const doll = new THREE.Group()
  doll.position.copy(pos)

  const sz = 0.5 + rng() * 0.2

  // String
  const stringGeo = new THREE.CylinderGeometry(0.015, 0.015, sz * 2, 4)
  const stringMesh = new THREE.Mesh(stringGeo, mats.string)
  stringMesh.position.y = sz * 1
  doll.add(stringMesh)

  // Head (sphere)
  const headGeo = new THREE.SphereGeometry(sz * 0.8, 12, 10)
  const headMat = mats.cloth.clone()
  const headMesh = new THREE.Mesh(headGeo, headMat)
  headMesh.position.y = sz * 2 + sz * 0.3
  headMesh.name = 'dollHead'
  headMesh.castShadow = true
  doll.add(headMesh)

  // Face - eyes
  const eyeGeo = new THREE.SphereGeometry(sz * 0.08, 6, 6)
  const eyeMat = new THREE.MeshStandardMaterial({ color: 0x3c2814, roughness: 0.9 })
  const leftEye = new THREE.Mesh(eyeGeo, eyeMat)
  leftEye.position.set(-sz * 0.2, sz * 2 + sz * 0.35, sz * 0.7)
  doll.add(leftEye)
  const rightEye = new THREE.Mesh(eyeGeo, eyeMat)
  rightEye.position.set(sz * 0.2, sz * 2 + sz * 0.35, sz * 0.7)
  doll.add(rightEye)

  // Mouth
  const mouthCurve = new THREE.EllipseCurve(0, 0, sz * 0.12, sz * 0.08, 0, Math.PI, false)
  const mouthPts = mouthCurve.getPoints(8)
  const mouthGeo = new THREE.BufferGeometry().setFromPoints(mouthPts)
  const mouthLine = new THREE.Line(mouthGeo, new THREE.LineBasicMaterial({ color: 0x3c2814 }))
  mouthLine.position.set(0, sz * 2 + sz * 0.1, sz * 0.72)
  doll.add(mouthLine)

  // Body (cone)
  const bodyGeo = new THREE.ConeGeometry(sz * 0.9, sz * 2.2, 8)
  const bodyMat = mats.cloth.clone()
  bodyMat.side = THREE.DoubleSide
  const bodyMesh = new THREE.Mesh(bodyGeo, bodyMat)
  bodyMesh.position.y = sz * 0.6
  bodyMesh.castShadow = true
  doll.add(bodyMesh)

  // Cheek blush (for real-page dolls)
  if (hasPage) {
    const blushGeo = new THREE.SphereGeometry(sz * 0.12, 6, 6)
    const blushMat = new THREE.MeshStandardMaterial({
      color: 0xf0a08c, transparent: true, opacity: 0.35, roughness: 1,
    })
    const leftBlush = new THREE.Mesh(blushGeo, blushMat)
    leftBlush.position.set(-sz * 0.35, sz * 2 + sz * 0.2, sz * 0.62)
    doll.add(leftBlush)
    const rightBlush = new THREE.Mesh(blushGeo, blushMat)
    rightBlush.position.set(sz * 0.35, sz * 2 + sz * 0.2, sz * 0.62)
    doll.add(rightBlush)
  }

  // ---- Spirit rings (魂环) — only for real pages ----
  if (hasPage) {
    const ringRng = createRng(branch.branchId * 37 + 42)
    const ringCount = 1 + Math.floor(ringRng() * 4)
    const ringColors = [0xdcdcf0, 0xffd732, 0xb464ff, 0x323246, 0xff3232, 0xff8c00]

    for (let i = 0; i < ringCount; i++) {
      const colorIdx = Math.floor(ringRng() * ringColors.length)
      const ringRadius = sz * (1.2 + ringRng() * 0.8)
      const ringTubeRadius = 0.03 + ringRng() * 0.02

      const ringGeo = new THREE.TorusGeometry(ringRadius, ringTubeRadius, 8, 32)
      const ringMat = new THREE.MeshStandardMaterial({
        color: ringColors[colorIdx],
        emissive: ringColors[colorIdx],
        emissiveIntensity: 0.6,
        transparent: true,
        opacity: 0.7,
        roughness: 0.3,
        metalness: 0.5,
      })

      const ringMesh = new THREE.Mesh(ringGeo, ringMat)
      ringMesh.position.y = sz * 2 + sz * 0.3 // at head center
      ringMesh.rotation.x = Math.PI / 2 + (ringRng() - 0.5) * 0.6
      ringMesh.rotation.z = ringRng() * Math.PI
      ringMesh.userData.spinSpeed = 0.3 + ringRng() * 0.5
      ringMesh.userData.spinAxis = new THREE.Vector3(
        ringRng() - 0.5, 1, ringRng() - 0.5
      ).normalize()
      ringMesh.name = 'spiritRing'
      doll.add(ringMesh)
    }
  }

  // Add sway data for animation
  doll.userData.swayFreq = 0.8 + (branch.branchId % 5) * 0.15
  doll.userData.swayPhase = branch.branchId * 2.3
  doll.userData.isDoll = true

  return doll
}

// ---- Ground ----

function createGround(mats: TreeMaterials): THREE.Mesh {
  const geo = new THREE.CircleGeometry(25, 48)
  geo.rotateX(-Math.PI / 2)
  const mesh = new THREE.Mesh(geo, mats.ground)
  mesh.position.y = -0.1
  mesh.receiveShadow = true
  return mesh
}

// ---- Grass (instanced + shader) ----

function createGrass(mats: TreeMaterials, rng: () => number): THREE.Mesh {
  const count = 3000
  const bladeH = 0.6
  const bladeW = 0.08

  // Blade shape
  const shape = new THREE.Shape()
  shape.moveTo(-bladeW / 2, 0)
  shape.quadraticCurveTo(-bladeW / 4, bladeH * 0.6, 0, bladeH)
  shape.quadraticCurveTo(bladeW / 4, bladeH * 0.6, bladeW / 2, 0)
  shape.closePath()

  const bladeGeo = new THREE.ShapeGeometry(shape, 3)

  // InstancedMesh
  const grassMat = new THREE.ShaderMaterial({
    uniforms: {
      uTime: { value: 0 },
      uGrowth: { value: 0 },
      uColor1: { value: new THREE.Color(0x1a5c2e) },
      uColor2: { value: new THREE.Color(0x3a8c4e) },
    },
    vertexShader: `
      uniform float uTime;
      uniform float uGrowth;
      varying vec2 vUv;
      varying float vHeight;

      void main() {
        vUv = uv;
        vHeight = uv.y;

        vec3 pos = position;
        // Sway based on height
        float sway = sin(uTime * 1.5 + instanceMatrix[3][0] * 0.5 + instanceMatrix[3][2] * 0.3) * pos.y * 0.3 * uGrowth;
        pos.x += sway;
        pos *= uGrowth;

        vec4 worldPos = instanceMatrix * vec4(pos, 1.0);
        gl_Position = projectionMatrix * modelViewMatrix * worldPos;
      }
    `,
    fragmentShader: `
      uniform vec3 uColor1;
      uniform vec3 uColor2;
      varying vec2 vUv;
      varying float vHeight;

      void main() {
        vec3 col = mix(uColor1, uColor2, vHeight);
        gl_FragColor = vec4(col, 0.85);
      }
    `,
    transparent: true,
    side: THREE.DoubleSide,
  })

  const grass = new THREE.InstancedMesh(bladeGeo, grassMat, count)

  const dummy = new THREE.Object3D()
  for (let i = 0; i < count; i++) {
    const angle = rng() * Math.PI * 2
    const radius = 1 + rng() * 20
    dummy.position.set(
      Math.cos(angle) * radius,
      0,
      Math.sin(angle) * radius,
    )
    dummy.rotation.y = rng() * Math.PI
    dummy.scale.set(0.6 + rng() * 0.8, 0.5 + rng() * 1.0, 1)
    dummy.updateMatrix()
    grass.setMatrixAt(i, dummy.matrix)
  }
  grass.instanceMatrix.needsUpdate = true

  return grass
}

// ---- Roots ----

function createRoots(rng: () => number, mats: TreeMaterials): THREE.Mesh[] {
  const rootDefs = [
    { angle: -0.6, len: 3, thick: 0.25 },
    { angle: -0.3, len: 2.2, thick: 0.18 },
    { angle: 0.2, len: 2.5, thick: 0.2 },
    { angle: 0.5, len: 2.8, thick: 0.22 },
    { angle: -0.85, len: 1.8, thick: 0.14 },
    { angle: 0.75, len: 2.0, thick: 0.15 },
  ]

  return rootDefs.map((r) => {
    const start = new THREE.Vector3(r.angle * 1.5, 0, (rng() - 0.5) * 1.5)
    const end = new THREE.Vector3(
      start.x + Math.cos(r.angle) * r.len,
      -0.5 - rng() * 0.5,
      start.z + Math.sin(r.angle) * r.len * 0.3,
    )
    const mid = start.clone().lerp(end, 0.5).add(new THREE.Vector3((rng() - 0.5) * 0.5, -0.3, (rng() - 0.5) * 0.3))

    const curve = new THREE.QuadraticBezierCurve3(start, mid, end)
    const tubeGeo = new THREE.TubeGeometry(curve, 8, Math.max(0.04, r.thick), 6, false)

    const mesh = new THREE.Mesh(tubeGeo, mats.rootBark)
    mesh.castShadow = true
    return mesh
  })
}

// ---- Trunk ----

function createTrunk(mats: TreeMaterials): THREE.Group {
  const trunkGroup = new THREE.Group()

  // Main trunk — tapered cylinder
  const trunkGeo = new THREE.CylinderGeometry(0.4, 1.2, 8, 12, 8, false)

  // Displace vertices for organic shape
  const pos = trunkGeo.attributes.position
  const rng = createRng(1234)
  for (let i = 0; i < pos.count; i++) {
    const x = pos.getX(i), y = pos.getY(i), z = pos.getZ(i)
    const dist = Math.sqrt(x * x + z * z)
    if (dist > 0.1) {
      const angle = Math.atan2(z, x)
      const noise = (rng() - 0.5) * 0.15 * (dist / 1.2)
      pos.setX(i, x + Math.cos(angle) * noise)
      pos.setZ(i, z + Math.sin(angle) * noise)
    }
  }
  pos.needsUpdate = true
  trunkGeo.computeVertexNormals()

  const trunkMesh = new THREE.Mesh(trunkGeo, mats.trunkBark)
  trunkMesh.position.y = 4
  trunkMesh.castShadow = true
  trunkMesh.receiveShadow = true
  trunkGroup.add(trunkMesh)

  return trunkGroup
}

// ---- Fireflies ----

function createFireflies(rng: () => number): THREE.Points {
  const count = 60
  const positions = new Float32Array(count * 3)
  const sizes = new Float32Array(count)
  const phases = new Float32Array(count)

  for (let i = 0; i < count; i++) {
    positions[i * 3] = (rng() - 0.5) * 24
    positions[i * 3 + 1] = 2 + rng() * 14
    positions[i * 3 + 2] = (rng() - 0.5) * 24
    sizes[i] = 0.1 + rng() * 0.2
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

      void main() {
        vec4 mvPos = modelViewMatrix * vec4(position, 1.0);
        float pulse = 0.4 + 0.6 * (0.5 + 0.5 * sin(uTime * 1.5 + aPhase));
        vAlpha = pulse;
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
        gl_FragColor = vec4(1.0, 0.92, 0.6, vAlpha * glow * 0.8);
      }
    `,
    transparent: true,
    depthWrite: false,
    blending: THREE.AdditiveBlending,
  })

  const points = new THREE.Points(geo, mat)
  points.userData.fireflyMat = mat
  return points
}
