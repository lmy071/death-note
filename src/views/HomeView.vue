<template>
  <div class="honkai-home">
    <!-- Background layers -->
    <div class="bg-stars"></div>
    <div class="bg-hexgrid"></div>

    <!-- Scanline overlay -->
    <div class="scanline-overlay"></div>

    <!-- HUD corner brackets -->
    <div class="hud-corner hud-corner--tl"></div>
    <div class="hud-corner hud-corner--tr"></div>
    <div class="hud-corner hud-corner--bl"></div>
    <div class="hud-corner hud-corner--br"></div>

    <!-- Top scanning line -->
    <div class="scan-line"></div>

    <!-- Header -->
    <header class="home-header">
      <div class="title-wrapper">
        <h1 class="home-title" data-text="DEATH NOTE">DEATH NOTE</h1>
      </div>
      <div class="subtitle-line">
        <span class="subtitle-bracket">&gt;</span>
        <span class="home-subtitle">点击枝丫，探索世界</span>
        <span class="cursor-blink">█</span>
      </div>
    </header>

    <!-- Main content -->
    <main class="tree-main">
      <div class="glass-panel">
        <WorldTree />
      </div>
    </main>

    <!-- Bottom HUD decoration -->
    <div class="hud-bottom-bar">
      <span class="hud-data">SYS.STATUS: <em class="cyan">ONLINE</em></span>
      <span class="hud-data">SECTOR: <em class="gold">WORLD_TREE</em></span>
      <span class="hud-data">LINK: <em class="magenta">STABLE</em></span>
    </div>
  </div>
</template>

<script setup lang="ts">
import WorldTree from '../components/WorldTree.vue'
</script>

<style scoped>
/* ========================================
   CSS Variables — Honkai 3rd Color Palette
   ======================================== */
.honkai-home {
  --bg-deep: #050816;
  --bg-panel: #0a1628;
  --cyan: #00d4ff;
  --magenta: #ff4488;
  --gold: #f0c040;
  --text: #e6e8ef;
  --text-dim: rgba(230, 232, 239, 0.45);
  --cyan-glow: rgba(0, 212, 255, 0.35);
  --magenta-glow: rgba(255, 68, 136, 0.3);
  --glass-bg: rgba(10, 22, 40, 0.55);
  --glass-border: rgba(0, 212, 255, 0.12);
}

/* ========================================
   Base Layout
   ======================================== */
.honkai-home {
  position: relative;
  height: 100vh;
  width: 100vw;
  display: flex;
  flex-direction: column;
  align-items: center;
  box-sizing: border-box;
  background: radial-gradient(ellipse at 50% 80%, #0a1628 0%, #050816 50%, #02010a 100%);
  overflow: hidden;
  font-family: 'Rajdhani', 'Orbitron', monospace;
  color: var(--text);
}

/* ========================================
   Background — Animated Star Particles
   ======================================== */
.bg-stars {
  position: absolute;
  inset: 0;
  z-index: 0;
  overflow: hidden;
}

.bg-stars::before,
.bg-stars::after {
  content: '';
  position: absolute;
  width: 2px;
  height: 2px;
  border-radius: 50%;
  background: transparent;
  box-shadow:
    /* Row 1 — scattered stars */
    25px 18px 0 0 rgba(0, 212, 255, 0.7),
    98px 42px 0 0 rgba(255, 255, 255, 0.5),
    210px 85px 0 0 rgba(0, 212, 255, 0.4),
    340px 22px 0 0 rgba(255, 255, 255, 0.6),
    480px 55px 0 0 rgba(255, 68, 136, 0.5),
    620px 30px 0 0 rgba(0, 212, 255, 0.6),
    780px 70px 0 0 rgba(255, 255, 255, 0.4),
    920px 15px 0 0 rgba(0, 212, 255, 0.5),
    1050px 48px 0 0 rgba(255, 255, 255, 0.3),
    1180px 90px 0 0 rgba(255, 68, 136, 0.4),
    /* Row 2 */
    55px 160px 0 0 rgba(255, 255, 255, 0.5),
    180px 200px 0 0 rgba(0, 212, 255, 0.6),
    310px 175px 0 0 rgba(255, 255, 255, 0.3),
    450px 210px 0 0 rgba(255, 68, 136, 0.5),
    590px 185px 0 0 rgba(0, 212, 255, 0.4),
    720px 195px 0 0 rgba(255, 255, 255, 0.6),
    860px 165px 0 0 rgba(0, 212, 255, 0.5),
    1000px 205px 0 0 rgba(255, 255, 255, 0.4),
    1140px 180px 0 0 rgba(255, 68, 136, 0.3),
    1250px 155px 0 0 rgba(0, 212, 255, 0.6),
    /* Row 3 */
    40px 300px 0 0 rgba(255, 68, 136, 0.4),
    150px 340px 0 0 rgba(255, 255, 255, 0.5),
    280px 310px 0 0 rgba(0, 212, 255, 0.6),
    420px 355px 0 0 rgba(255, 255, 255, 0.3),
    560px 325px 0 0 rgba(0, 212, 255, 0.5),
    700px 345px 0 0 rgba(255, 68, 136, 0.4),
    830px 300px 0 0 rgba(255, 255, 255, 0.6),
    960px 360px 0 0 rgba(0, 212, 255, 0.3),
    1100px 330px 0 0 rgba(255, 255, 255, 0.5),
    1220px 350px 0 0 rgba(255, 68, 136, 0.6),
    /* Row 4 */
    70px 460px 0 0 rgba(0, 212, 255, 0.5),
    200px 500px 0 0 rgba(255, 255, 255, 0.4),
    330px 480px 0 0 rgba(255, 68, 136, 0.5),
    470px 510px 0 0 rgba(0, 212, 255, 0.3),
    600px 475px 0 0 rgba(255, 255, 255, 0.6),
    740px 495px 0 0 rgba(0, 212, 255, 0.4),
    870px 470px 0 0 rgba(255, 68, 136, 0.5),
    1010px 505px 0 0 rgba(255, 255, 255, 0.3),
    1150px 485px 0 0 rgba(0, 212, 255, 0.6),
    1280px 460px 0 0 rgba(255, 255, 255, 0.5),
    /* Row 5 */
    35px 620px 0 0 rgba(255, 255, 255, 0.4),
    170px 660px 0 0 rgba(0, 212, 255, 0.5),
    300px 640px 0 0 rgba(255, 68, 136, 0.6),
    440px 670px 0 0 rgba(255, 255, 255, 0.3),
    580px 630px 0 0 rgba(0, 212, 255, 0.4),
    710px 655px 0 0 rgba(255, 255, 255, 0.5),
    850px 625px 0 0 rgba(255, 68, 136, 0.4),
    990px 665px 0 0 rgba(0, 212, 255, 0.6),
    1120px 645px 0 0 rgba(255, 255, 255, 0.4),
    1260px 635px 0 0 rgba(0, 212, 255, 0.5);
  animation: starDrift 60s linear infinite;
}

.bg-stars::after {
  width: 1px;
  height: 1px;
  animation-delay: -30s;
  animation-duration: 80s;
  box-shadow:
    80px 50px 0 0 rgba(255, 255, 255, 0.3),
    220px 120px 0 0 rgba(0, 212, 255, 0.4),
    370px 30px 0 0 rgba(255, 68, 136, 0.3),
    510px 140px 0 0 rgba(255, 255, 255, 0.5),
    650px 60px 0 0 rgba(0, 212, 255, 0.3),
    800px 110px 0 0 rgba(255, 255, 255, 0.4),
    940px 45px 0 0 rgba(255, 68, 136, 0.5),
    1080px 130px 0 0 rgba(0, 212, 255, 0.4),
    1200px 75px 0 0 rgba(255, 255, 255, 0.3),
    1300px 100px 0 0 rgba(0, 212, 255, 0.5),
    60px 250px 0 0 rgba(0, 212, 255, 0.3),
    190px 290px 0 0 rgba(255, 255, 255, 0.4),
    350px 270px 0 0 rgba(255, 68, 136, 0.4),
    500px 310px 0 0 rgba(0, 212, 255, 0.5),
    640px 260px 0 0 rgba(255, 255, 255, 0.3),
    790px 285px 0 0 rgba(0, 212, 255, 0.4),
    930px 245px 0 0 rgba(255, 68, 136, 0.5),
    1070px 300px 0 0 rgba(255, 255, 255, 0.4),
    1190px 270px 0 0 rgba(0, 212, 255, 0.3),
    1320px 255px 0 0 rgba(255, 255, 255, 0.5),
    100px 420px 0 0 rgba(255, 68, 136, 0.3),
    250px 450px 0 0 rgba(0, 212, 255, 0.5),
    400px 400px 0 0 rgba(255, 255, 255, 0.4),
    540px 440px 0 0 rgba(0, 212, 255, 0.3),
    680px 430px 0 0 rgba(255, 68, 136, 0.4),
    820px 460px 0 0 rgba(255, 255, 255, 0.5),
    970px 415px 0 0 rgba(0, 212, 255, 0.4),
    1110px 450px 0 0 rgba(255, 255, 255, 0.3),
    1240px 425px 0 0 rgba(255, 68, 136, 0.5),
    1340px 440px 0 0 rgba(0, 212, 255, 0.3);
}

@keyframes starDrift {
  0% { transform: translateY(0); }
  100% { transform: translateY(-30px); }
}

/* ========================================
   Background — Hexagonal Grid Overlay
   ======================================== */
.bg-hexgrid {
  position: absolute;
  inset: 0;
  z-index: 1;
  opacity: 0.04;
  background-image:
    linear-gradient(30deg, var(--cyan) 12%, transparent 12.5%, transparent 87%, var(--cyan) 87.5%, var(--cyan)),
    linear-gradient(150deg, var(--cyan) 12%, transparent 12.5%, transparent 87%, var(--cyan) 87.5%, var(--cyan)),
    linear-gradient(30deg, var(--cyan) 12%, transparent 12.5%, transparent 87%, var(--cyan) 87.5%, var(--cyan)),
    linear-gradient(150deg, var(--cyan) 12%, transparent 12.5%, transparent 87%, var(--cyan) 87.5%, var(--cyan)),
    linear-gradient(60deg, var(--magenta) 25%, transparent 25.5%, transparent 75%, var(--magenta) 75%, var(--magenta)),
    linear-gradient(60deg, var(--magenta) 25%, transparent 25.5%, transparent 75%, var(--magenta) 75%, var(--magenta));
  background-size: 56px 98px;
  background-position: 0 0, 0 0, 28px 49px, 28px 49px, 0 0, 28px 49px;
  pointer-events: none;
}

/* ========================================
   Scanline Overlay (CRT-style)
   ======================================== */
.scanline-overlay {
  position: absolute;
  inset: 0;
  z-index: 2;
  pointer-events: none;
  background: repeating-linear-gradient(
    0deg,
    transparent,
    transparent 2px,
    rgba(0, 0, 0, 0.03) 2px,
    rgba(0, 0, 0, 0.03) 4px
  );
}

/* ========================================
   HUD Corner Brackets
   ======================================== */
.hud-corner {
  position: absolute;
  z-index: 10;
  width: 40px;
  height: 40px;
  pointer-events: none;
}

.hud-corner::before,
.hud-corner::after {
  content: '';
  position: absolute;
  background: var(--cyan);
  box-shadow: 0 0 8px var(--cyan-glow), 0 0 20px var(--cyan-glow);
  animation: bracketPulse 3s ease-in-out infinite;
}

/* Top-left */
.hud-corner--tl {
  top: 16px;
  left: 16px;
}
.hud-corner--tl::before {
  top: 0; left: 0; width: 24px; height: 2px;
}
.hud-corner--tl::after {
  top: 0; left: 0; width: 2px; height: 24px;
}

/* Top-right */
.hud-corner--tr {
  top: 16px;
  right: 16px;
}
.hud-corner--tr::before {
  top: 0; right: 0; width: 24px; height: 2px;
}
.hud-corner--tr::after {
  top: 0; right: 0; width: 2px; height: 24px;
}

/* Bottom-left */
.hud-corner--bl {
  bottom: 16px;
  left: 16px;
}
.hud-corner--bl::before {
  bottom: 0; left: 0; width: 24px; height: 2px;
}
.hud-corner--bl::after {
  bottom: 0; left: 0; width: 2px; height: 24px;
}

/* Bottom-right */
.hud-corner--br {
  bottom: 16px;
  right: 16px;
}
.hud-corner--br::before {
  bottom: 0; right: 0; width: 24px; height: 2px;
}
.hud-corner--br::after {
  bottom: 0; right: 0; width: 2px; height: 24px;
}

@keyframes bracketPulse {
  0%, 100% {
    opacity: 0.6;
    box-shadow: 0 0 4px var(--cyan-glow);
  }
  50% {
    opacity: 1;
    box-shadow: 0 0 12px var(--cyan-glow), 0 0 28px var(--cyan-glow);
  }
}

/* ========================================
   Scanning Line (Horizontal Sweep)
   ======================================== */
.scan-line {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 2px;
  z-index: 11;
  pointer-events: none;
  background: linear-gradient(90deg, transparent, var(--cyan), transparent);
  box-shadow: 0 0 15px var(--cyan), 0 0 40px var(--cyan-glow);
  animation: scanSweep 4s ease-in-out infinite;
  opacity: 0;
}

@keyframes scanSweep {
  0% {
    top: 0%;
    opacity: 0;
  }
  5% {
    opacity: 0.8;
  }
  95% {
    opacity: 0.8;
  }
  100% {
    top: 100%;
    opacity: 0;
  }
}

/* ========================================
   Header Section
   ======================================== */
.home-header {
  position: relative;
  z-index: 5;
  text-align: center;
  padding: 32px 20px 12px;
  flex-shrink: 0;
}

.title-wrapper {
  position: relative;
  display: inline-block;
}

/* ========================================
   Glitch Title — "DEATH NOTE"
   ======================================== */
.home-title {
  font-family: 'Orbitron', 'Rajdhani', monospace;
  font-size: 48px;
  font-weight: 900;
  letter-spacing: 8px;
  color: var(--text);
  position: relative;
  margin: 0;
  text-transform: uppercase;
  animation: glitchText 4s infinite;
}

/* Pseudo-elements for glitch clip-path slicing */
.home-title::before,
.home-title::after {
  content: attr(data-text);
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  pointer-events: none;
}

.home-title::before {
  color: var(--cyan);
  animation: glitchSlice1 4s infinite;
  clip-path: inset(0 0 65% 0);
}

.home-title::after {
  color: var(--magenta);
  animation: glitchSlice2 4s infinite;
  clip-path: inset(65% 0 0 0);
}

@keyframes glitchText {
  0%, 92%, 100% {
    text-shadow:
      0 0 10px rgba(0, 212, 255, 0.2),
      0 0 30px rgba(255, 68, 136, 0.1);
  }
  93% {
    text-shadow:
      -3px 0 var(--cyan),
      3px 0 var(--magenta);
  }
  94% {
    text-shadow:
      2px 0 var(--magenta),
      -2px 0 var(--cyan),
      0 0 20px var(--cyan-glow);
  }
  95% {
    text-shadow:
      -1px 0 var(--cyan),
      1px 0 var(--magenta);
  }
  96% {
    text-shadow:
      3px 0 var(--magenta),
      -3px 0 var(--cyan),
      0 0 30px var(--magenta-glow);
  }
  97% {
    text-shadow:
      0 0 10px rgba(0, 212, 255, 0.2),
      0 0 30px rgba(255, 68, 136, 0.1);
  }
}

@keyframes glitchSlice1 {
  0%, 92%, 97%, 100% {
    transform: translate(0);
  }
  93% {
    transform: translate(-4px, -1px);
  }
  95% {
    transform: translate(3px, 1px);
  }
  96% {
    transform: translate(-2px, 0);
  }
}

@keyframes glitchSlice2 {
  0%, 92%, 97%, 100% {
    transform: translate(0);
  }
  93% {
    transform: translate(4px, 1px);
  }
  95% {
    transform: translate(-3px, -1px);
  }
  96% {
    transform: translate(2px, 0);
  }
}

/* ========================================
   Subtitle with Terminal Cursor
   ======================================== */
.subtitle-line {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 4px;
  margin-top: 8px;
}

.subtitle-bracket {
  color: var(--cyan);
  font-family: 'Rajdhani', monospace;
  font-weight: 700;
  font-size: 14px;
  opacity: 0.7;
}

.home-subtitle {
  font-family: 'Rajdhani', monospace;
  font-size: 15px;
  font-weight: 500;
  color: var(--text-dim);
  letter-spacing: 3px;
}

.cursor-blink {
  font-family: monospace;
  font-size: 14px;
  color: var(--cyan);
  animation: cursorBlink 1s step-end infinite;
}

@keyframes cursorBlink {
  0%, 50% { opacity: 1; }
  51%, 100% { opacity: 0; }
}

/* ========================================
   Glass Panel — WorldTree Container
   ======================================== */
.tree-main {
  position: relative;
  z-index: 5;
  flex: 1;
  width: 100%;
  min-height: 0;
  padding: 8px 24px;
  box-sizing: border-box;
}

.glass-panel {
  width: 100%;
  height: 100%;
  border: 1px solid var(--glass-border);
  border-radius: 4px;
  background: var(--glass-bg);
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
  box-shadow:
    0 0 20px rgba(0, 212, 255, 0.05),
    inset 0 0 30px rgba(0, 0, 0, 0.3);
  overflow: hidden;
  position: relative;
}

/* Glass panel corner accents */
.glass-panel::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  width: 60px;
  height: 1px;
  background: linear-gradient(90deg, var(--cyan), transparent);
  opacity: 0.6;
}

.glass-panel::after {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  width: 1px;
  height: 60px;
  background: linear-gradient(180deg, var(--cyan), transparent);
  opacity: 0.6;
}

/* ========================================
   Bottom HUD Bar
   ======================================== */
.hud-bottom-bar {
  position: relative;
  z-index: 5;
  width: 100%;
  display: flex;
  justify-content: center;
  gap: 32px;
  padding: 8px 20px 14px;
  flex-shrink: 0;
  font-family: 'Rajdhani', monospace;
  font-size: 11px;
  letter-spacing: 2px;
  text-transform: uppercase;
  color: var(--text-dim);
}

.hud-data {
  opacity: 0.5;
}

.hud-data em {
  font-style: normal;
  font-weight: 700;
}

.hud-data .cyan {
  color: var(--cyan);
  text-shadow: 0 0 6px var(--cyan-glow);
}

.hud-data .gold {
  color: var(--gold);
  text-shadow: 0 0 6px rgba(240, 192, 64, 0.3);
}

.hud-data .magenta {
  color: var(--magenta);
  text-shadow: 0 0 6px var(--magenta-glow);
}

/* ========================================
   Responsive Adjustments
   ======================================== */
@media (max-width: 768px) {
  .home-title {
    font-size: 28px;
    letter-spacing: 4px;
  }

  .home-header {
    padding: 20px 16px 8px;
  }

  .tree-main {
    padding: 4px 12px;
  }

  .hud-bottom-bar {
    gap: 16px;
    font-size: 9px;
  }

  .hud-corner {
    width: 28px;
    height: 28px;
  }

  .hud-corner--tl::before,
  .hud-corner--tr::before,
  .hud-corner--bl::before,
  .hud-corner--br::before {
    width: 16px;
  }

  .hud-corner--tl::after,
  .hud-corner--tr::after,
  .hud-corner--bl::after,
  .hud-corner--br::after {
    height: 16px;
  }
}

@media (max-width: 480px) {
  .home-title {
    font-size: 22px;
    letter-spacing: 3px;
  }

  .home-subtitle {
    font-size: 12px;
    letter-spacing: 1px;
  }

  .hud-bottom-bar {
    flex-direction: column;
    align-items: center;
    gap: 4px;
  }
}
</style>
