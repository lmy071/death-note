<template>
  <div ref="wrap" class="cube-container">
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
    <div v-if="twistKeys.length" class="twist-bar">
      <button v-for="k in twistKeys" :key="k" class="twist-btn" @click.stop="handleBtn(k)">{{ k }}</button>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, onUnmounted, ref, reactive } from 'vue'

const props = defineProps({
  size: { type: Number, default: 280 },
  scale: { type: Number, default: 38 },
  autoRotate: { type: Boolean, default: true },
  showControls: { type: Boolean, default: false },
})

const cvs = ref(null)
const wrap = ref(null)
let animId = null, ctx = null
let canvasW = 0, canvasH = 0, dpr = 1
let rotY = 0.5, rotX = -0.35
let dragging = false, autoRotate_ = props.autoRotate
let lastX = 0, lastY = 0

/* ════════════════════ COLORS ════════════════════ */
const FACE_COLORS = {
  U:'#FFFFFF', D:'#FFD500',
  F:'#B71234', B:'#FF5800',
  R:'#0046AD', L:'#009B48',
}
const FACE_NAMES = ['U','D','F','B','R','L']
const FACE_NORMALS = {
  U:[0,1,0], D:[0,-1,0], F:[0,0,1], B:[0,0,-1], R:[1,0,0], L:[-1,0,0],
}

/* ════════════════════ CUBIE DATA ════════════════════ */
const cubies = reactive([])

function initSolved() {
  cubies.length = 0
  for (let ix=0;ix<3;ix++)
    for (let iy=0;iy<3;iy++)
      for (let iz=0;iz<3;iz++)
        cubies.push({ix,iy,iz,
          fc:{U:iy===2?FACE_COLORS.U:null,D:iy===0?FACE_COLORS.D:null,
              F:iz===2?FACE_COLORS.F:null,B:iz===0?FACE_COLORS.B:null,
              R:ix===2?FACE_COLORS.R:null,L:ix===0?FACE_COLORS.L:null},
        })
}

function visibleFaces(c) {
  const out=[]
  for(const f of FACE_NAMES){
    if(c.fc[f]===null) continue
    const n=FACE_NORMALS[f]
    if(n[0]!==0&&c.ix!==(n[0]>0?2:0)) continue
    if(n[1]!==0&&c.iy!==(n[1]>0?2:0)) continue
    if(n[2]!==0&&c.iz!==(n[2]>0?2:0)) continue
    out.push(f)
  }
  return out
}

/* ════════════════════ TWIST ════════════════════ */
let isTwisting=false, twistInfo=null
const TWIST_DUR=200

const CYCLES={
  y_p1_l2:['F','R','B','L'], y_m1_l2:['F','L','B','R'],
  y_m1_l0:['F','R','B','L'], y_p1_l0:['F','L','B','R'],
  x_p1_l2:['U','F','D','B'], x_m1_l2:['U','B','D','F'],
  x_m1_l0:['U','F','D','B'], x_p1_l0:['U','B','D','F'],
  z_p1_l2:['U','R','D','L'], z_m1_l2:['U','L','D','R'],
  z_m1_l0:['U','R','D','L'], z_p1_l0:['U','L','D','R'],
}
function rotAxis(rx,ry,rz,axis,a){
  const c=Math.cos(a),s=Math.sin(a)
  if(axis==='y')return[c*rx-s*rz,ry,s*rx+c*rz]
  if(axis==='x')return[rx,c*ry-s*rz,s*ry+c*rz]
  return[c*rx-s*ry,s*rx+c*ry,rz]
}
function applyTwist(axis,sign,lvl){
  const aff=[]
  for(const c of cubies)
    if((axis==='x'&&c.ix===lvl)||(axis==='y'&&c.iy===lvl)||(axis==='z'&&c.iz===lvl))
      aff.push(c)
  const a=-sign*Math.PI/2
  for(const c of aff){
    const[nx,ny,nz]=rotAxis(c.ix-1,c.iy-1,c.iz-1,axis,a)
    c.ix=Math.round(nx+1);c.iy=Math.round(ny+1);c.iz=Math.round(nz+1)
  }
  const cyc=CYCLES[`${axis}_${sign>0?'p1':'m1'}_l${lvl}`]
  if(!cyc)return
  for(const c of aff){const[a,b,d,e]=cyc,t=c.fc[a];c.fc[a]=c.fc[e];c.fc[e]=c.fc[d];c.fc[d]=c.fc[b];c.fc[b]=t}
}
function twist(key){
  if(isTwisting)return
  const m={U:{a:'y',s:1,l:2},"U'":{a:'y',s:-1,l:2},D:{a:'y',s:-1,l:0},"D'":{a:'y',s:1,l:0},
    R:{a:'x',s:1,l:2},"R'":{a:'x',s:-1,l:2},L:{a:'x',s:-1,l:0},"L'":{a:'x',s:1,l:0},
    F:{a:'z',s:1,l:2},"F'":{a:'z',s:-1,l:2},B:{a:'z',s:-1,l:0},"B'":{a:'z',s:1,l:0}}
  const t=m[key];if(!t)return
  const aff=[]
  for(const c of cubies)if((t.a==='x'&&c.ix===t.l)||(t.a==='y'&&c.iy===t.l)||(t.a==='z'&&c.iz===t.l))aff.push(c)
  isTwisting=true;autoRotate_=false
  twistInfo={...t,st:performance.now(),aff,cyc:CYCLES[`${t.a}_${t.s>0?'p1':'m1'}_l${t.l}`]}
}
function scramble(n=20){
  const k=['U',"U'",'D',"D'",'R',"R'",'L',"L'",'F',"F'",'B',"B'"]
  for(let i=0;i<n;i++){
    const key=k[Math.random()*k.length|0],f=key[0],p=key.includes("'")
    const fm={U:{a:'y',s:p?-1:1,l:2},D:{a:'y',s:!p?-1:1,l:0},R:{a:'x',s:p?-1:1,l:2},L:{a:'x',s:!p?-1:1,l:0},F:{a:'z',s:p?-1:1,l:2},B:{a:'z',s:!p?-1:1,l:0}}
    const info=fm[f];if(info)applyTwist(info.a,info.s,info.l)
  }
}
function handleBtn(k){k==='🔀'?scramble():twist(k)}
const twistKeys=computed(()=>props.showControls?['U',"U'",'D',"D'",'R',"R'",'L',"L'",'F',"F'",'B',"B'",'🔀']:[])

/* ════════════════════ RENDER — ORTHOGRAPHIC ISOMETRIC ════════════════════ */

// Face quads in local unit-cube coords (CCW from outside)
const QUADS={
  R:[[1,0,0],[1,1,0],[1,1,1],[1,0,1]],
  L:[[0,0,1],[0,1,1],[0,1,0],[0,0,0]],
  U:[[0,1,0],[1,1,0],[1,1,1],[0,1,1]],
  D:[[0,0,1],[1,0,1],[1,0,0],[0,0,0]],
  F:[[0,0,1],[1,0,1],[1,1,1],[0,1,1]],
  B:[[0,1,0],[1,1,0],[1,0,0],[0,0,0]],
}

/**
 * Isometric-like orthographic projection.
 * Camera at [1,1,1] looking at origin → gives classic isometric view.
 */
function isoProject(x,y,z,cx,cy,s){
  // Rotate to isometric view: 45° around Y then ~35.264° around X
  // Combined transform:
  // screenX = (x - z) * cos(45°) * s + cx
  // screenY = -y*s + (x+z)*sin(35.264°)*s + cy
  // Simplified with cos(45°)=√2/2≈0.7071, sin(35.264°)=√(1/3)≈0.5774
  const ISO_COS = 0.70710678  // √2/2
  const ISO_SIN = 0.57735027  // 1/√3
  return {
    x: cx + (x - z) * ISO_COS * s,
    y: cy - y * s + (x + z) * ISO_SIN * s,
  }
}

/** Transform 3×3 matrix × vector */
function m3v(m,v){return[m[0][0]*v[0]+m[0][1]*v[1]+m[0][2]*v[2],m[1][0]*v[0]+m[1][1]*v[1]+m[1][2]*v[2],m[2][0]*v[0]+m[2][1]*v[1]+m[2][2]*v[2]]}

/** Build Y-then-X rotation matrix */
function rotMat(ry,rx){
  const cy=Math.cos(ry),sy=Math.sin(ry),cx=Math.cos(rx),sx=Math.sin(rx)
  return[[cy,0,-sy],[sy*sx,cx,cy*sx],[sy*cx,-sx,cy*cx]]
}

function shade(hex,k){
  const r=parseInt(hex.slice(1,3),16),g=parseInt(hex.slice(3,5),16),b=parseInt(hex.slice(5,7),16)
  return`rgb(${Math.min(255,Math.max(0,r*k|0))},${Math.min(255,Math.max(0,g*k|0))},${Math.min(255,Math.max(0,b*k|0))})`
}

function render(now){
  const el=cvs.value;if(!el||!ctx)return
  ctx.clearRect(0,0,canvasW,canvasH)

  let tAngle=0
  if(isTwisting&&twistInfo){
    const e=now-twistInfo.st
    tAngle=Math.min(1,e/TWIST_DUR)*(Math.PI/2)
    if(e>=TWIST_DUR){applyTwist(twistInfo.a,twistInfo.s,twistInfo.l);isTwisting=false;twistInfo=null;tAngle=0;if(props.autoRotate)autoRotate_=true}
  }

  if(autoRotate_&&!dragging)rotY+=0.006

  const M=rotMat(rotY,rotX)
  const cx=canvasW/2, cy=canvasH/2+8
  const S=props.scale

  const drawList=[]

  for(const c of cubies){
    // Compute world positions of all 8 corners
    const wVerts=[]
    for(let i=0;i<8;i++){
      const v=[[0,0,0],[1,0,0],[1,1,0],[0,1,0],[0,0,1],[1,0,1],[1,1,1],[0,1,1]][i]
      let px=c.ix+v[0]-1,py=c.iy+v[1]-1,pz=c.iz+v[2]-1
      if(twistInfo&&twistInfo.aff.includes(c)){const sa=-twistInfo.s*tAngle;[px,py,pz]=rotAxis(px,py,pz,twistInfo.a,sa)}
      wVerts.push(m3v(M,[px,py,pz]))
    }

    // Average Z for sort (camera looks down -Z after rotation)
    let avgZ=0;for(const v of wVerts)avgZ+=v[2];avgZ/=8

    // Face colors during animation
    const fc={}
    if(twistInfo&&twistInfo.aff.includes(c)&&twistInfo.cyc){
      const[a,b,d,e]=twistInfo.cyc
      for(const f of FACE_NAMES)fc[f]=(f===a?c.fc[e]:f===b?c.fc[a]:f===d?c.fc[b]:f===e?c.fc[d]:c.fc[f])
    }else Object.assign(fc,c.fc)

    for(const f of visibleFaces(c)){
      const col=fc[f];if(!col)continue

      // Transformed face normal
      const rn=m3v(M,FACE_NORMALS[f])
      // Back-face cull: normal must face camera (positive Z in view space)
      if(rn[2]<=0)continue

      // Project quad corners
      const q=QUADS[f]
      const crnrs=q.map(([qx,qy,qz])=>{
        let px=c.ix+qx-1,py=c.iy+qy-1,pz=c.iz+qz-1
        if(twistInfo&&twistInfo.aff.includes(c)){const sa=-twistInfo.s*tAngle;[px,py,pz]=rotAxis(px,py,pz,twistInfo.a,sa)}
        const r=m3v(M,[px,py,pz])
        return isoProject(r[0],r[1],r[2],cx,cy,S)
      })

      // 2D winding check
      const cross=(crnrs[1].x-crnrs[0].x)*(crnrs[2].y-crnrs[0].y)-(crnrs[1].y-crnrs[0].y)*(crnrs[2].x-crnrs[0].x)
      if(cross<=0)continue

      // Shade based on face orientation
      const yLight=(rn[1]+1)/2 // 0..1
      const fMap={U:1.0,F:0.72,R:0.55,L:0.50,B:0.58,D:0.32}
      const k=(fMap[f]||0.55)*(0.58+0.42*yLight)

      drawList.push({crnrs,color:shade(col,k),z:avgZ})
    }
  }

  // Painter's algorithm: far → near (smaller Z first since camera looks down -Z)
  drawList.sort((a,b)=>a.z-b.z)

  for(const d of drawList){
    ctx.beginPath()
    ctx.moveTo(d.crnrs[0].x,d.crnrs[0].y)
    for(let i=1;i<d.crnrs.length;i++)ctx.lineTo(d.crnrs[i].x,d.crnrs[i].y)
    ctx.closePath()
    ctx.fillStyle=d.color
    ctx.fill()
    ctx.strokeStyle='rgba(0,0,0,0.22)'
    ctx.lineWidth=0.7
    ctx.stroke()
  }

  animId=requestAnimationFrame(render)
}

/* ════════════════════ CANVAS SETUP ════════════════════ */
function setupCanvas(){
  const el=cvs.value;if(!el)return
  dpr=Math.min(window.devicePixelRatio||1,2)
  canvasW=props.size;canvasH=props.size
  el.width=canvasW*dpr;el.height=canvasH*dpr
  el.style.width=canvasW+'px';el.style.height=canvasH+'px'
  ctx=el.getContext('2d')
  ctx.scale(dpr,dpr)
}

/* ════════════════════ INPUT ════════════════════ */
function onMouseDown(e){dragging=true;lastX=e.clientX;lastY=e.clientY;autoRotate_=false}
function onMouseMove(e){
  if(!dragging)return
  rotY+=(e.clientX-lastX)*0.008;rotX-=(e.clientY-lastY)*0.008
  rotX=Math.max(-1.4,Math.min(0.7,rotX));lastX=e.clientX;lastY=e.clientY
}
function onMouseUp(){dragging=false;if(props.autoRotate&&!isTwisting)autoRotate_=true}
function onTouchStart(e){dragging=true;lastX=e.touches[0].clientX;lastY=e.touches[0].clientY;autoRotate_=false}
function onTouchMove(e){
  if(!dragging)return
  rotY+=(e.touches[0].clientX-lastX)*0.008;rotX-=(e.touches[0].clientY-lastY)*0.008
  rotX=Math.max(-1.4,Math.min(0.7,rotX));lastX=e.touches[0].clientX;lastY=e.touches[0].clientY
}
function onKeyDown(e){
  if(isTwisting)return
  const m={u:'U',U:'U',d:'D',r:'R',l:'L',f:'F',b:'B'}
  let k=m[e.key];if(!k)return;if(e.shiftKey)k+="'";twist(k)
}

onMounted(()=>{initSolved();setupCanvas();animId=requestAnimationFrame(render);window.addEventListener('keydown',onKeyDown)})
onUnmounted(()=>{if(animId)cancelAnimationFrame(animId);window.removeEventListener('keydown',onKeyDown)})
defineExpose({scramble,cubies})
</script>

<style scoped>
.cube-container{display:flex;flex-direction:column;align-items:center;gap:8px}
.cube-canvas{display:block;border-radius:12px;cursor:grab;background:rgba(0,0,0,0.15)}
.cube-canvas:active{cursor:grabbing}
.twist-bar{display:flex;flex-wrap:wrap;gap:4px;justify-content:center;max-width:360px}
.twist-btn{
  font-size:11px;font-weight:700;font-family:ui-monospace,monospace;
  padding:4px 9px;border-radius:8px;border:1px solid rgba(255,255,255,0.14);
  background:rgba(255,255,255,0.06);color:#e6e8ef;cursor:pointer;
  transition:background .12s,border-color .12s
}
.twist-btn:hover{background:rgba(130,177,255,0.18);border-color:rgba(130,177,255,0.4)}
</style>
