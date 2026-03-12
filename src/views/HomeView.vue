<template>
  <div class="home">
    <header class="home-header">
      <h1 class="home-title">Death Note</h1>
      <p class="home-subtitle">选择一个功能页面开始使用</p>
    </header>

    <main class="home-main">
      <section class="home-grid">
        <router-link class="home-card" to="/notion">
          <h2 class="home-card__title">重启脑语（Notion）</h2>
          <p class="home-card__desc">打开内嵌 Notion 页，专注阅读 / 记录。</p>
        </router-link>

        <router-link class="home-card" to="/leetcode">
          <h2 class="home-card__title">LeetCode 题解</h2>
          <p class="home-card__desc">浏览 `src/leetCode` 下的所有题解源码。</p>
        </router-link>
      </section>
    </main>
  </div>
</template>

<script setup>
</script>

<style scoped>
.home {
  min-height: 100vh;
  width: 100vw;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: flex-start;
  padding: 40px 20px;
  box-sizing: border-box;
  background: radial-gradient(circle at top, #151b2f 0, #050816 55%, #02010a 100%);
  color: #e6e8ef;
}

.home-header {
  text-align: center;
  margin-bottom: 32px;
}

.home-title {
  font-size: 32px;
  font-weight: 800;
  margin: 0 0 8px;
}

.home-subtitle {
  margin: 0;
  font-size: 14px;
  color: rgba(230, 232, 239, 0.75);
}

.home-main {
  width: 100%;
  max-width: 720px;
}

.home-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 18px;
}

.home-card {
  display: block;
  padding: 18px 18px 16px;
  border-radius: 16px;
  background: rgba(10, 16, 32, 0.95);
  border: 1px solid rgba(255, 255, 255, 0.08);
  text-decoration: none;
  color: inherit;
  transition: transform 0.18s ease-out, box-shadow 0.18s ease-out,
    border-color 0.18s ease-out, background 0.18s ease-out;
}

.home-card:hover {
  transform: translateY(-3px) translateZ(0);
  background: rgba(18, 28, 60, 0.98);
  border-color: rgba(130, 177, 255, 0.6);
  box-shadow: 0 16px 35px rgba(2, 8, 38, 0.8);
}

.home-card__title {
  margin: 0 0 6px;
  font-size: 18px;
  font-weight: 700;
}

.home-card__desc {
  margin: 0;
  font-size: 13px;
  color: rgba(230, 232, 239, 0.78);
}
</style>

