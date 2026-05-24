<template>
  <div class="detail">
    <header class="detail-bar">
      <router-link to="/" class="back-btn">← 返回首页</router-link>
      <h1 class="detail-title">魔方</h1>
      <span class="detail-badge">3×3×3</span>
    </header>

    <main class="detail-body">
      <section class="cube-stage">
        <RubiksCube :size="480" :scale="48" />
      </section>

      <section class="info-panel">
        <div class="info-item">
          <span class="info-icon">🎨</span>
          <div>
            <h4>标准配色</h4>
            <p>白 / 黄 · 红 / 橙 · 蓝 / 绿</p>
          </div>
        </div>
        <div class="info-item">
          <span class="info-icon">🖱️</span>
          <div>
            <h4>交互方式</h4>
            <p>拖拽旋转 · 自动旋转 · 触屏支持</p>
          </div>
        </div>
        <div class="info-item">
          <span class="info-icon">⚙️</span>
          <div>
            <h4>实现方案</h4>
            <p>Canvas 2D · 数学投影 · 背剔除 · 画家算法</p>
          </div>
        </div>
      </section>
    </main>
  </div>
</template>

<script setup>
import RubiksCube from '../../components/RubiksCube.vue'
</script>

<style scoped>
.detail {
  min-height: 100vh;
  width: 100vw;
  background: radial-gradient(circle at top, #151b2f 0, #050816 55%, #02010a 100%);
  display: flex;
  flex-direction: column;
  align-items: center;
}

.detail-bar {
  width: 100%;
  max-width: 960px;
  padding: 20px 24px 16px;
  display: flex;
  align-items: center;
  gap: 16px;
}

.back-btn {
  font-size: 14px;
  color: rgba(130, 177, 255, 0.85);
  text-decoration: none;
  font-weight: 600;
  transition: color 0.15s;
  flex-shrink: 0;
}
.back-btn:hover {
  color: rgba(160, 200, 255, 1);
}

.detail-title {
  font-size: 22px;
  font-weight: 750;
  color: #e6e8ef;
  margin: 0;
}

.detail-badge {
  font-size: 12px;
  font-weight: 650;
  padding: 3px 10px;
  border-radius: 999px;
  background: rgba(130, 177, 255, 0.14);
  color: rgba(200, 218, 255, 0.95);
  border: 1px solid rgba(130, 177, 255, 0.25);
}

.detail-body {
  flex: 1;
  width: 100%;
  max-width: 960px;
  padding: 0 24px 40px;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 32px;
}

.cube-stage {
  display: flex;
  justify-content: center;
  align-items: center;
}

.info-panel {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
  gap: 16px;
  width: 100%;
  max-width: 720px;
}

.info-item {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  padding: 16px;
  border-radius: 14px;
  background: rgba(10, 16, 32, 0.95);
  border: 1px solid rgba(255, 255, 255, 0.08);
}

.info-icon {
  font-size: 24px;
  line-height: 1;
  flex-shrink: 0;
  margin-top: 2px;
}

.info-item h4 {
  margin: 0 0 4px;
  font-size: 14px;
  font-weight: 700;
  color: #e6e8ef;
}

.info-item p {
  margin: 0;
  font-size: 13px;
  line-height: 1.5;
  color: rgba(230, 232, 239, 0.65);
}
</style>