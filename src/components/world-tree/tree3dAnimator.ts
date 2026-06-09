/**
 * 3D Tree animation — growth, sway, spirit ring rotation, fireflies
 */
import * as THREE from 'three'

export function animateTree3D(
  treeGroup: THREE.Group,
  growthProgress: number,
  time: number,
  grassUniforms: { uTime: { value: number }; uGrowth: { value: number } },
): void {
  // Update grass
  grassUniforms.uTime.value = time
  grassUniforms.uGrowth.value = growthProgress

  // Update fireflies
  treeGroup.traverse((child) => {
    // Growth animation
    if (child.userData.growthOrder !== undefined) {
      const order = child.userData.growthOrder
      const localProgress = Math.max(0, Math.min(1, (growthProgress - order) / (1 - order + 0.01)))
      const scale = easeOutCubic(localProgress)
      child.scale.set(scale, scale, scale)
    }

    // Doll sway
    if (child.userData.isDoll) {
      const freq = child.userData.swayFreq as number
      const phase = child.userData.swayPhase as number
      child.rotation.z = Math.sin(time * freq + phase) * 0.08
      child.rotation.x = Math.sin(time * freq * 0.7 + phase + 1) * 0.04
    }

    // Spirit ring rotation
    if (child.name === 'spiritRing') {
      const speed = child.userData.spinSpeed as number
      const axis = child.userData.spinAxis as THREE.Vector3
      child.rotateOnAxis(axis, speed * 0.016) // ~60fps

      // Pulsing emissive
      const mat = (child as THREE.Mesh).material as THREE.MeshStandardMaterial
      if (mat && mat.emissiveIntensity !== undefined) {
        mat.emissiveIntensity = 0.4 + 0.4 * Math.sin(time * 1.5 + child.id)
      }
    }

    // Firefly time uniform
    if (child.userData.fireflyMat) {
      const mat = child.userData.fireflyMat as THREE.ShaderMaterial
      mat.uniforms.uTime.value = time
    }
  })
}

function easeOutCubic(t: number): number {
  return 1 - Math.pow(1 - t, 3)
}
