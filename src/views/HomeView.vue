<template>
  <div class="home">
    <header class="home-header">
      <h1 class="home-title">Death Note</h1>
      <p class="home-subtitle">实用工具集</p>
    </header>

    <main class="waterfall">
      <!-- Card 1: LeetCode 题解 -->
      <router-link to="/code/leet-code" class="waterfall-card">
        <div class="card-head">
          <span class="card-icon">📖</span>
          <h3 class="card-name">LeetCode 题解</h3>
        </div>
        <p class="card-desc">浏览全部 {{ problemCount }} 道题解源码，支持语法高亮、搜索与复制。</p>
        <div class="card-link">浏览全部 →</div>
      </router-link>

      <!-- Card 2: 粒子效果（点击进入详情） -->
      <router-link
        to="/fun/particle-canvas"
        custom
        v-slot="{ navigate }"
      >
        <div
          class="waterfall-card"
          @click="navigate"
        >
          <div class="card-head">
            <span class="card-icon">✨</span>
            <h3 class="card-name">粒子特效</h3>
          </div>
          <div class="particle-wrap">
            <ParticleCanvas />
          </div>
          <p class="card-desc" style="margin-top:8px">鼠标移入 · 流光粒子 · 渐隐动画</p>
          <div class="card-link">查看详情 →</div>
        </div>
      </router-link>

      <!-- Card 3: 魔方（点击进入详情） -->
      <router-link
        to="/fun/rubiks-cube"
        custom
        v-slot="{ navigate }"
      >
        <div
          class="waterfall-card cube-card"
          @click="navigate"
        >
          <div class="card-head">
            <span class="card-icon">🎲</span>
            <h3 class="card-name">魔方</h3>
          </div>
          <div class="cube-wrap">
            <RubiksCube :size="260" />
          </div>
          <p class="card-desc" style="margin-top:8px">Canvas 绘制 · 拖拽旋转 · 标准配色</p>
          <div class="card-link">查看详情 →</div>
        </div>
      </router-link>

      <!-- Card 4: 折线图（点击进入详情） -->
      <router-link
        to="/fun/line-chart"
        custom
        v-slot="{ navigate }"
      >
        <div
          class="waterfall-card"
          @click="navigate"
        >
          <div class="card-head">
            <span class="card-icon">📈</span>
            <h3 class="card-name">折线图</h3>
          </div>
          <div class="chart-preview">
            <LineChart
              :options="miniChart"
              :height="180"
            />
          </div>
          <p class="card-desc" style="margin-top:4px">Canvas 绘制 · 平滑曲线 · 面积填充 · 悬浮提示</p>
          <div class="card-link">查看详情 →</div>
        </div>
      </router-link>
    </main>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import RubiksCube from '../components/RubiksCube.vue'
import ParticleCanvas from '../components/ParticleCanvas.vue'
import LineChart from '../components/LineChart.vue'

const problemCount = computed(() => {
  const m = import.meta.glob('../leetCode/*.js', { eager: true })
  return Object.keys(m).length
})

const miniChart = {
  xAxis: { data: ['1月', '2月', '3月', '4月', '5月', '6月'] },
  yAxis: { splitNumber: 3 },
  legend: false,
  series: [
    { name: '销售额', data: [120, 200, 150, 280, 220, 310], area: true },
    { name: '利润', data: [40, 75, 55, 100, 85, 120] }
  ]
}
</script>

<style scoped>
.home {
  min-height: 100vh;
  width: 100vw;
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 40px 20px 60px;
  box-sizing: border-box;
  background: radial-gradient(circle at top, #151b2f 0, #050816 55%, #02010a 100%);
}

/* ---- Header ---- */
.home-header {
  text-align: center;
  margin-bottom: 32px;
}
.home-title {
  font-size: 32px;
  font-weight: 800;
  color: #e6e8ef;
  margin: 0 0 8px;
}
.home-subtitle {
  font-size: 14px;
  color: rgba(230, 232, 239, 0.75);
  margin: 0;
}

/* ---- Waterfall ---- */
.waterfall {
  column-count: 3;
  column-gap: 16px;
  max-width: 960px;
  width: 100%;
  padding: 0;
}

@media (max-width: 860px) {
  .waterfall { column-count: 2; max-width: 640px; }
}
@media (max-width: 560px) {
  .waterfall { column-count: 1; max-width: 380px; }
}

/* ---- Card ---- */
.waterfall-card {
  break-inside: avoid;
  margin-bottom: 16px;
  padding: 18px;
  border-radius: 14px;
  background: rgba(10, 16, 32, 0.95);
  border: 1px solid rgba(255, 255, 255, 0.08);
  text-decoration: none;
  color: inherit;
  display: block;
  cursor: pointer;
  transition: transform 0.18s ease-out,
              box-shadow 0.18s ease-out,
              border-color 0.18s ease-out,
              background 0.18s ease-out;
}
.waterfall-card:hover {
  transform: translateY(-3px) translateZ(0);
  background: rgba(18, 28, 60, 0.98);
  border-color: rgba(130, 177, 255, 0.6);
  box-shadow: 0 16px 35px rgba(2, 8, 38, 0.8);
}

/* Card head */
.card-head {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 10px;
}
.card-icon {
  font-size: 22px;
  line-height: 1;
}
.card-name {
  font-size: 16px;
  font-weight: 700;
  color: #e6e8ef;
  margin: 0;
}

.card-desc {
  font-size: 13px;
  line-height: 1.5;
  color: rgba(230, 232, 239, 0.65);
  margin: 0;
}

.card-link {
  margin-top: 10px;
  font-size: 13px;
  font-weight: 600;
  color: rgba(130, 177, 255, 0.85);
  transition: color 0.15s;
}
.waterfall-card:hover .card-link {
  color: rgba(160, 200, 255, 1);
}

/* Cube wrapper */
.cube-wrap, .particle-wrap {
  display: flex;
  justify-content: center;
  align-items: center;
  margin-top: 6px;
}

/* Chart preview in card */
.chart-preview {
  margin: 6px -18px 0 -18px;
  overflow: hidden;
  border-radius: 8px;
}


</style>