<template>
  <div id="layout">
    <RouterView v-slot="{ Component }">
      <KeepAlive :include="keepAliveInclude" :max="7" @vue:mounted="onKeepAliveMounted">
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
import { watch, type VNode } from 'vue'
import { useRoute } from 'vue-router'
import {
  useKeepAliveStore,
  initKeepAliveStore,
  registerRouteNameMapping,
  registerKeepAliveInstance,
  syncWithVueInternal,
} from './composables/useKeepAliveStore'

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

/**
 * KeepAlive 组件挂载时，获取其组件实例
 * 通过 instance.__v_cache 可以读取 Vue 内部的真实缓存 Map
 */
function onKeepAliveMounted(vnode: VNode) {
  // vnode.component 就是 KeepAlive 的组件实例
  const instance = (vnode as any).component
  if (instance) {
    registerKeepAliveInstance(instance)
    // 初始同步一次
    syncWithVueInternal()
  }
}

// 路由切换时：
// 1. 自动将目标组件加入缓存（内部会检查 removedSet 和 autoCache 开关）
// 2. 同步 Vue 内部缓存状态，确保 Store 与 Vue 一致
watch(
  () => route.path,
  (path) => {
    onRouteChange(path)
    // 延迟同步，等 Vue KeepAlive 内部完成缓存操作后再读取
    // 使用 queuePostRenderEffect 或 setTimeout 确保 DOM 更新后
    setTimeout(() => {
      const result = syncWithVueInternal()
      if (result.added.length > 0 || result.removed.length > 0) {
        console.log(
          '[KeepAliveStore] 同步修正:',
          result.added.length ? `补入 ${result.added.join(', ')}` : '',
          result.removed.length ? `移除 ${result.removed.join(', ')}` : '',
        )
      }
    }, 0)
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
