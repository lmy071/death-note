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
  refreshCacheSnapshot,
} from './composables/useKeepAliveStore'

const route = useRoute()

initKeepAliveStore()

registerRouteNameMapping('/', 'HomeView', '首页')
registerRouteNameMapping('/code/leet-code', 'leetCodeView', 'LeetCode 题解')
registerRouteNameMapping('/md/md-note', 'mdNoteView', '笔记')
registerRouteNameMapping('/fun/line-chart', 'LineChartView', '折线图')
registerRouteNameMapping('/fun/particle-canvas', 'particleCanvasView', '粒子特效')
registerRouteNameMapping('/dev/cache-inspector', 'CacheInspectorView', '缓存管理器')

const { include: keepAliveInclude, onRouteChange } = useKeepAliveStore()

function onKeepAliveMounted(vnode: VNode) {
  const instance = (vnode as any).component
  if (instance) {
    registerKeepAliveInstance(instance)
    refreshCacheSnapshot()
  }
}

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
