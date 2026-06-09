/**
 * 3D Tree animation — growth, crystal hover/rotation, data ring spin, data particles
 */
import * as THREE from 'three'

export function animateTree3D(
  treeGroup: THREE.Group,
  growthProgress: number,
  time: number,
  grassUniforms: { uTime: { value: number }; uGrowth: { value: number } },
): void {
  // Update grid particles (replaces grass uniforms)
  grassUniforms.uTime.value = time
  grassUniforms.uGrowth.value = growthProgress

  // Update data particles
  treeGroup.traverse((child: THREE.Object3D) => {
    // Growth animation
    if (child.userData.growthOrder !== undefined) {
      const order = child.userData.growthOrder
      const localProgress = Math.max(0, Math.min(1, (growthProgress - order) / (1 - order + 0.01)))
      const scale = easeOutCubic(localProgress)
      child.scale.set(scale, scale, scale)
    }

    // Crystal hover and slow rotation (replaces doll sway)
    if (child.userData.isDoll) {
      const freq = child.userData.swayFreq as number
      const phase = child.userData.swayPhase as number
      const floatPhase = child.userData.floatPhase as number || 0

      // Gentle hover float
      child.position.y += Math.sin(time * freq * 0.5 + floatPhase) * 0.001

      // Slow rotation of entire crystal group
      child.rotation.y = time * 0.3 + phase * 0.1

      // Subtle tilt
      child.rotation.z = Math.sin(time * freq * 0.3 + phase) * 0.04
      child.rotation.x = Math.sin(time * freq * 0.2 + phase + 1) * 0.02
    }

    // Data ring rotation (replaces spirit ring rotation)
    if (child.name === 'spiritRing') {
      const speed = child.userData.spinSpeed as number
      const axis = child.userData.spinAxis as THREE.Vector3
      child.rotateOnAxis(axis, speed * 0.016)

      // Pulsing emissive — cyan/magenta pulse
      const mat = (child as THREE.Mesh).material as THREE.MeshStandardMaterial
      if (mat && mat.emissiveIntensity !== undefined) {
        mat.emissiveIntensity = 0.4 + 0.5 * Math.sin(time * 1.5 + child.id)
      }
    }

    // Data particle time uniform
    if (child.userData.fireflyMat) {
      const mat = child.userData.fireflyMat as THREE.ShaderMaterial
      mat.uniforms.uTime.value = time
    }
  })
}

function easeOutCubic(t: number): number {
  return 1 - Math.pow(1 - t, 3)
}
