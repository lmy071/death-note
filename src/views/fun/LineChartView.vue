<template>
  <div class="chart-view">
    <header class="view-header">
      <router-link to="/" class="back-btn">← 返回</router-link>
      <h1>Canvas 折线图</h1>
      <p class="subtitle">纯 Canvas 实现 · 平滑曲线 · 面积填充 · 交互动效</p>
    </header>

    <main class="chart-gallery">
      <!-- Chart 1: 多系列折线 -->
      <section class="chart-card">
        <h3>📊 多系列折线图</h3>
        <LineChart :options="chart1" :height="360" />
      </section>

      <!-- Chart 2: 面积图 -->
      <section class="chart-card">
        <h3>🏔️ 面积图</h3>
        <LineChart :options="chart2" :height="360" />
      </section>

      <!-- Chart 3: 大量数据点 -->
      <section class="chart-card">
        <h3>📈 密集数据</h3>
        <LineChart :options="chart3" :height="340" />
      </section>
    </main>
  </div>
</template>

<script setup lang="ts">
import LineChart from '../../components/LineChart.vue'

interface ChartConfig {
  xAxis: { data: string[] }
  yAxis: { splitNumber?: number }
  series: Array<{
    name?: string
    data: number[]
    area?: boolean
    color?: string
    areaOpacity?: number
    smooth?: boolean
    lineWidth?: number
  }>
}

const chart1: ChartConfig = {
  xAxis: { data: ['1月', '2月', '3月', '4月', '5月', '6月', '7月'] },
  yAxis: { splitNumber: 6 },
  series: [
    { name: '销售额', data: [120, 200, 150, 280, 220, 310, 400], area: true },
    { name: '利润', data: [40, 75, 55, 100, 85, 120, 160], area: true },
    { name: '成本', data: [80, 125, 95, 180, 135, 190, 240] }
  ]
}

const chart2: ChartConfig = {
  xAxis: { data: ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'] },
  yAxis: { splitNumber: 5 },
  series: [
    {
      name: 'UV',
      data: [4200, 3800, 5100, 4600, 5900, 6800, 5500],
      area: true,
      color: '#b388ff',
      areaOpacity: 0.25
    },
    {
      name: 'PV',
      data: [8500, 7900, 10200, 9300, 11800, 14500, 11200],
      area: true,
      areaOpacity: 0.15
    }
  ]
}

const chart3: ChartConfig = {
  xAxis: {
    data: Array.from({ length: 24 }, (_, i) => `${i}:00`)
  },
  yAxis: { splitNumber: 6 },
  series: [
    {
      name: 'CPU %',
      data: [23, 18, 15, 12, 10, 8, 12, 22, 35, 48, 55, 60,
             58, 52, 45, 42, 38, 35, 40, 55, 68, 62, 48, 32],
      smooth: true,
      area: true,
      lineWidth: 1.5,
      areaOpacity: 0.12
    },
    {
      name: 'Memory %',
      data: [45, 44, 43, 42, 41, 40, 41, 43, 46, 50, 55, 62,
             65, 64, 62, 60, 58, 57, 58, 60, 63, 61, 55, 48],
      smooth: true,
      area: true,
      lineWidth: 1.5,
      areaOpacity: 0.12
    }
  ]
}
</script>

<style scoped>
.chart-view {
  min-height: 100vh;
  width: 100vw;
  padding: 40px 20px 80px;
  box-sizing: border-box;
  background: radial-gradient(circle at top, #151b2f 0, #050816 55%, #02010a 100%);
  display: flex;
  flex-direction: column;
  align-items: center;
}

.view-header {
  text-align: center;
  margin-bottom: 40px;
  position: relative;
}
.back-btn {
  position: absolute;
  left: 0;
  top: 0;
  font-size: 14px;
  color: rgba(130, 177, 255, 0.85);
  text-decoration: none;
  transition: color 0.15s;
}
.back-btn:hover { color: rgba(160, 200, 255, 1); }
.view-header h1 {
  font-size: 28px;
  font-weight: 800;
  color: #e6e8ef;
  margin: 0 0 8px;
}
.subtitle {
  font-size: 14px;
  color: rgba(230, 232, 239, 0.55);
  margin: 0;
}

.chart-gallery {
  max-width: 800px;
  width: 100%;
  display: flex;
  flex-direction: column;
  gap: 32px;
}

.chart-card {
  background: rgba(10, 16, 36, 0.95);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 16px;
  padding: 24px 20px 20px;
}
.chart-card h3 {
  font-size: 16px;
  font-weight: 700;
  color: #e6e8ef;
  margin: 0 0 16px;
}
</style>
