<template>
  <div id="layout">
    <RouterView v-slot="{ Component }">
      <KeepAlive :include="keepAliveInclude">
        <component :is="Component" />
      </KeepAlive>
    </RouterView>
  </div>
</template>

<script lang="ts">
export default {
  name: 'App'
}
</script>

<script setup lang="ts">
import { watch } from 'vue'
import { useRoute } from 'vue-router'
import { useKeepAliveStore, initKeepAliveStore, registerRouteNameMapping } from './composables/useKeepAliveStore'

const route = useRoute()

// 初始化 KeepAlive Store
initKeepAliveStore()

// 手动注册路由 path → 组件 name 映射（含显示标签）
registerRouteNameMapping('/', 'HomeView', '首页')
registerRouteNameMapping('/code/leet-code', 'leetCodeView', 'LeetCode 题解')
registerRouteNameMapping('/md/md-note', 'mdNoteView', '笔记')
registerRouteNameMapping('/fun/line-chart', 'LineChartView', '折线图')
registerRouteNameMapping('/fun/particle-canvas', 'particleCanvasView', '粒子特效')
registerRouteNameMapping('/dev/cache-inspector', 'CacheInspectorView', '缓存管理器')

const { include: keepAliveInclude, onRouteChange } = useKeepAliveStore()

// 路由切换时自动将目标组件加入缓存（内部会检查 removedSet 和 autoCache 开关）
watch(
  () => route.path,
  (path) => {
    onRouteChange(path)
  },
  { immediate: true }
)
</script>

<style>
#app,
#layout {
  font-family: Avenir, Helvetica, Arial, sans-serif;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
  text-align: center;
  color: #2c3e50;
	height: 100vh;
	width: 100vw;
	position: relative;
	margin: 0;
	padding: 0;
}
</style>
