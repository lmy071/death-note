<template>
  <canvas
    ref="cvs"
    class="cube-canvas"
    @mousedown="onMouseDown"
    @mousemove="onMouseMove"
    @mouseup="onMouseUp"
    @mouseleave="onMouseUp"
    @touchstart.prevent="onTouchStart"
    @touchmove.prevent="onTouchMove"
    @touchend="onMouseUp"
  ></canvas>
</template>

<script setup>
import { ref, onMounted, onUnmounted, watch } from 'vue'

const props = defineProps({
  /** Canvas 尺寸（正方形），默认 280 */
  size: { type: Number, default: 280 },
  /** 单位缩放，默认 38 */
  scale: { type: Number, default: 38 },
  /** 是否自动旋转 */
  autoRotate: { type: Boolean, default: true },
})

const cvs = ref(null)
let animId = null
let rotY = 0.5
let rotX = -0.35
let dragging = false
let lastX = 0, lastY = 0
let autoRotating = props.autoRotate

/* ---- 颜色 & 常量 ---- */
const COS30 = Math.cos(Math.PI / 6)
const SIN30 = Math.sin(Math.PI / 6)

const FACE_COLOR = {
  top:    '#FFFFFF',
  bottom: '#FFD500',
  front:  '#B71234',
  back:   '#FF5800',
  right:  '#0046AD',
  left:   '#009B48',
}

const FACES = {
  right:  { idx: [1,5,7,3], normal: [ 1, 0, 0] },
  left:   { idx: [0,2,6,4], normal: [-1, 0, 0] },
  top:    { idx: [2,3,7,6], normal: [ 0, 1, 0] },
  bottom: { idx: [0,4,5,1], normal: [ 0,-1, 0] },
  front:  { idx: [4,5,7,6], normal: [ 0, 0, 1] },
  back:   { idx: [0,1,3,2], normal: [ 0, 0,-1] },
}

const V = [
  [0,0,0],[1,0,0],[0,1,0],[1,1,0],
  [0,0,1],[1,0,1],[0,1,1],[1,1,1],
]

/* ---- 3D 工具 ---- */
function mulMat(a,b){
  const r=[[0,0,0],[0,0,0],[0,0,0]]
  for(let i=0;i<3;i++) for(let j=0;j<3;j++) for(let k=0;k<3;k++)
    r[i][j]+=a[i][k]*b[k][j]
  return r
}
function rotYMat(a){const c=Math.cos(a),s=Math.sin(a);return[[c,0,-s],[0,1,0],[s,0,c]]}
function rotXMat(a){const c=Math.cos(a),s=Math.sin(a);return[[1,0,0],[0,c,s],[0,-s,c]]}
function transform(pt,mat){
  return[mat[0][0]*pt[0]+mat[0][1]*pt[1]+mat[0][2]*pt[2],
         mat[1][0]*pt[0]+mat[1][1]*pt[1]+mat[1][2]*pt[2],
         mat[2][0]*pt[0]+mat[2][1]*pt[1]+mat[2][2]*pt[2]]
}
function project(px,py,pz,cx,cy,s){
  return{
    x:cx+(px-pz)*COS30*s,
    y:cy+(px+pz)*SIN30*s-py*s
  }
}
function shade(hex,k){
  const r=parseInt(hex.slice(1,3),16),g=parseInt(hex.slice(3,5),16),b=parseInt(hex.slice(5,7),16)
  return `rgb(${Math.min(255,Math.round(r*k))},${Math.min(255,Math.round(g*k))},${Math.min(255,Math.round(b*k))})`
}
function faceColor(x,y,z,face){
  if(face==='top'    && y===2) return FACE_COLOR.top
  if(face==='bottom' && y===0) return FACE_COLOR.bottom
  if(face==='front'  && z===2) return FACE_COLOR.front
  if(face==='back'   && z===0) return FACE_COLOR.back
  if(face==='right'  && x===2) return FACE_COLOR.right
  if(face==='left'   && x===0) return FACE_COLOR.left
  return null
}

/* ---- 渲染 ---- */
function render(){
  const el=cvs.value; if(!el) return
  const ctx=el.getContext('2d')
  const w=el.width, h=el.height
  ctx.clearRect(0,0,w,h)

  if(autoRotating && !dragging) rotY+=0.005

  const Ry=rotYMat(rotY), Rx=rotXMat(rotX)
  const R=mulMat(Ry,Rx)
  const cx=w/2, cy=h/2+10
  const S=props.scale

  const cubies=[]
  for(let ix=0;ix<3;ix++)
    for(let iy=0;iy<3;iy++)
      for(let iz=0;iz<3;iz++){
        const verts=V.map(([vx,vy,vz])=>{
          const p=[ix+vx-1,iy+vy-1,iz+vz-1]
          const r=transform(p,R)
          return {...project(r[0],r[1],r[2],cx,cy,S),r}
        })
        let zd=0; for(const v of verts) zd+=v.r[0]+v.r[1]+v.r[2]; zd/=verts.length
        cubies.push({ix,iy,iz,verts,zd})
      }
  cubies.sort((a,b)=>a.zd-b.zd)

  for(const cb of cubies){
    for(const [name,face] of Object.entries(FACES)){
      const col=faceColor(cb.ix,cb.iy,cb.iz,name)
      if(!col) continue
      const rn=transform(face.normal,R)
      const dot=rn[0]+rn[1]+rn[2]
      if(dot<=0) continue
      const iv=face.idx
      const [p0,p1,p2]=[cb.verts[iv[0]],cb.verts[iv[1]],cb.verts[iv[2]]]
      if((p1.x-p0.x)*(p2.y-p0.y)-(p1.y-p0.y)*(p2.x-p0.x)<=0) continue

      ctx.beginPath(); ctx.moveTo(p0.x,p0.y)
      for(let i=1;i<iv.length;i++) ctx.lineTo(cb.verts[iv[i]].x,cb.verts[iv[i]].y)
      ctx.closePath()

      const ndot=Math.max(0.25,(rn[1]+1)/2)
      let light=0.5
      if(name==='top') light=1.0
      else if(name==='front') light=0.62
      else if(name==='right') light=0.48
      else if(name==='left') light=0.44
      else if(name==='back') light=0.52
      else if(name==='bottom') light=0.30
      ctx.fillStyle=shade(col, light*(0.6+0.4*ndot))
      ctx.fill()
      ctx.strokeStyle='rgba(0,0,0,0.18)'; ctx.lineWidth=0.6; ctx.stroke()
    }
  }
  animId=requestAnimationFrame(render)
}

/* ---- 交互 ---- */
function onMouseDown(e){ dragging=true; lastX=e.clientX; lastY=e.clientY; autoRotating=false }
function onMouseMove(e){
  if(!dragging) return
  rotY+= (e.clientX-lastX)*0.008
  rotX-= (e.clientY-lastY)*0.008
  rotX=Math.max(-1.2,Math.min(0.4,rotX))
  lastX=e.clientX; lastY=e.clientY
}
function onMouseUp(){ dragging=false; if(props.autoRotate) setTimeout(()=>{ autoRotating=true },1200) }

function onTouchStart(e){
  dragging=true; lastX=e.touches[0].clientX; lastY=e.touches[0].clientY; autoRotating=false
}
function onTouchMove(e){
  if(!dragging) return
  rotY+=(e.touches[0].clientX-lastX)*0.008
  rotX-=(e.touches[0].clientY-lastY)*0.008
  rotX=Math.max(-1.2,Math.min(0.4,rotX))
  lastX=e.touches[0].clientX; lastY=e.touches[0].clientY
}

onMounted(()=>{
  const el=cvs.value; el.width=props.size; el.height=props.size
  animId=requestAnimationFrame(render)
})
onUnmounted(()=>{ if(animId) cancelAnimationFrame(animId) })
</script>

<style scoped>
.cube-canvas{ display:block; width:100%; border-radius:12px; cursor:grab; }
.cube-canvas:active{ cursor:grabbing; }
</style>