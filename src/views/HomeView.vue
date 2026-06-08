<template>
  <div class="home">
    <header class="home-header">
      <h1 class="home-title">Death Note</h1>
      <p class="home-subtitle">点击枝丫，探索世界</p>
    </header>
    <main class="tree-main">
      <WorldTree />
    </main>
  </div>
</template>

<script setup lang="ts">
import WorldTree from '../components/WorldTree.vue'
</script>

<style scoped>
.home {
  height: 100vh;
  width: 100vw;
  display: flex;
  flex-direction: column;
  align-items: center;
  box-sizing: border-box;
  background: radial-gradient(ellipse at 50% 100%, #1a1208 0%, #0b0d18 40%, #050816 70%, #02010a 100%);
  overflow: hidden;
}

.home-header {
  text-align: center;
  padding: 24px 20px 8px;
  flex-shrink: 0;
}
.home-title {
  font-size: 32px;
  font-weight: 800;
  color: #f0c040;
  margin: 0 0 6px;
  text-shadow: 0 0 30px rgba(212, 160, 23, 0.3);
}
.home-subtitle {
  font-size: 14px;
  color: rgba(240, 192, 64, 0.6);
  margin: 0;
}

.tree-main {
  flex: 1;
  width: 100%;
  min-height: 0;
}
</style>
