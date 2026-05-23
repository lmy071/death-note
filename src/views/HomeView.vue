<template>
  <div class="home">
    <header text-center mb-32px>
      <h1 text-32px font-800 m-0 mb-8px text-body>Death Note</h1>
      <p text-14px text-dim m-0>选择一个功能页面开始使用</p>
    </header>

    <main w-full max-w-720px>
      <section grid grid-cols="[repeat(auto-fit,minmax(220px,1fr))]" gap-18px>
        <router-link class="home-card" to="/code/leet-code">
          <h2 text-18px font-700 m-0 mb-6px text-body>LeetCode 题解</h2>
          <p text-13px text-dim m-0>浏览 `src/leetCode` 下的所有题解源码。</p>
        </router-link>
      </section>
    </main>
  </div>
</template>

<script setup>
</script>

<style scoped>
/* 复杂样式保留：径向渐变背景 & 卡片交互动效 */
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
</style>

