import { ref, computed, type Component, type VNode } from 'vue'
import { useRouter } from 'vue-router'

/**
 * KeepAlive 缓存管理 Store
 *
 * 原则：展示数据只从 Vue KeepAlive 内部 __v_cache 获取，不额外存储
 * ──────────────────────────────────────────────
 * - includeList 仅驱动 <KeepAlive :include>，控制哪些组件可被缓存
 * - cacheInstances / cacheCount 等展示数据直接读取 __v_cache
 * - 删除操作：从 include 移除 → Vue 自动销毁 → 重新读取 __v_cache 即为最新
 * ──────────────────────────────────────────────
 */

export interface CacheInstance {
  /** 组件 name */
  name: string
  /** 对应的路由 path */
  routePath: string
  /** 是否为当前活跃实例 */
  isActive: boolean
}

// ---- 全局单例状态 ----

/** 缓存名单 —— 仅驱动 <KeepAlive :include> */
const includeList = ref<string[]>([])

/** 路由 path → 组件 name */
const routeNameMap = ref<Map<string, string>>(new Map())

/** 组件 name → 路由 path */
const nameRouteMap = ref<Map<string, string>>(new Map())

/** 组件 name → 显示标签 */
const nameLabelMap = ref<Map<string, string>>(new Map())

/** KeepAlive 组件实例引用 */
let keepAliveInstance: any = null

/** 上次读取的 __v_cache 快照（响应式，供 computed 消费） */
const cacheSnapshot = ref<string[]>([])

let routerInstance: ReturnType<typeof useRouter> | null = null

// ---- 初始化 ----

export function initKeepAliveStore() {
  const router = useRouter()
  routerInstance = router

  router.getRoutes().forEach((route) => {
    const comp = route.components?.default
    if (comp && typeof comp === 'object' && 'name' in comp) {
      const componentName = (comp as Component).name
      if (componentName) {
        routeNameMap.value.set(route.path, componentName)
        nameRouteMap.value.set(componentName, route.path)
      }
    }
  })
}

/**
 * 注册 KeepAlive 组件实例
 */
export function registerKeepAliveInstance(instance: any) {
  keepAliveInstance = instance
}

/**
 * 从 Vue KeepAlive 内部 __v_cache 读取实际缓存的组件 name 列表
 * 返回按缓存顺序排列的数组（最旧在前，最新在后，与 Vue 内部 keys Set 顺序一致）
 */
function readVueCacheNames(): string[] {
  if (!keepAliveInstance) return []

  const cache: Map<any, VNode> | undefined = keepAliveInstance.__v_cache
  if (!cache) return []

  const names: string[] = []
  cache.forEach((vnode) => {
    const comp = vnode.type
    if (comp && typeof comp === 'object' && 'name' in comp) {
      const name = (comp as any).name
      if (typeof name === 'string') {
        names.push(name)
      }
    }
  })
  return names
}

/**
 * 刷新缓存快照（从 __v_cache 读取最新状态）
 * 在路由切换后 / 手动操作后调用
 */
export function refreshCacheSnapshot() {
  cacheSnapshot.value = readVueCacheNames()

  // 同步 includeList：将 Vue 内部已有但 include 没有的补上
  for (const name of cacheSnapshot.value) {
    if (!includeList.value.includes(name)) {
      includeList.value.push(name)
    }
  }
  // 将 Vue 内部已淘汰的从 include 移除
  const cached = new Set(cacheSnapshot.value)
  for (let i = includeList.value.length - 1; i >= 0; i--) {
    if (!cached.has(includeList.value[i])) {
      includeList.value.splice(i, 1)
    }
  }
}

// ---- 映射辅助 ----

function getComponentNameByPath(path: string): string | undefined {
  const direct = routeNameMap.value.get(path)
  if (direct) return direct
  if (routerInstance) {
    const matched = routerInstance.resolve(path)
    const comp = matched?.matched?.[0]?.components?.default
    if (comp && typeof comp === 'object' && 'name' in comp) {
      return (comp as Component).name
    }
  }
  return undefined
}

export function registerRouteNameMapping(path: string, componentName: string, label?: string) {
  routeNameMap.value.set(path, componentName)
  nameRouteMap.value.set(componentName, path)
  if (label) {
    nameLabelMap.value.set(componentName, label)
  }
  // 默认全部加入 include（允许被缓存）
  if (!includeList.value.includes(componentName)) {
    includeList.value.push(componentName)
  }
}

/** 导出 nameLabelMap */
export { nameLabelMap }

// ---- 主要 API ----

export function useKeepAliveStore() {
  const router = useRouter()
  routerInstance = router

  /** 驱动 <KeepAlive :include> 的列表 */
  const include = computed(() => includeList.value)

  /**
   * 缓存实例列表 —— 直接从 __v_cache 快照生成
   */
  const cacheInstances = computed<CacheInstance[]>(() => {
    const currentPath = router.currentRoute.value.path
    return cacheSnapshot.value.map((name) => {
      const routePath = nameRouteMap.value.get(name) ?? ''
      return {
        name,
        routePath,
        isActive: routePath === currentPath,
      }
    })
  })

  /** 缓存数量 —— 直接来自 __v_cache */
  const cacheCount = computed(() => cacheSnapshot.value.length)

  /**
   * 删除指定组件缓存
   * 从 include 列表移除 → Vue KeepAlive 自动销毁对应缓存实例 → 刷新快照
   */
  function removeCache(componentName: string) {
    const idx = includeList.value.indexOf(componentName)
    if (idx !== -1) {
      includeList.value.splice(idx, 1)
    }
    // Vue 会在下一个渲染周期销毁缓存，延迟刷新快照
    setTimeout(() => refreshCacheSnapshot(), 0)
  }

  function removeCacheByPath(routePath: string) {
    const compName = getComponentNameByPath(routePath)
    if (compName) removeCache(compName)
  }

  /**
   * 清空所有缓存
   */
  function clearAllCache() {
    includeList.value.splice(0, includeList.value.length)
    setTimeout(() => refreshCacheSnapshot(), 0)
  }

  function onRouteChange(path: string) {
    // 确保目标组件在 include 中
    const compName = getComponentNameByPath(path)
    if (compName && !includeList.value.includes(compName)) {
      includeList.value.push(compName)
    }
    // 延迟刷新快照，等 Vue 完成缓存操作
    setTimeout(() => refreshCacheSnapshot(), 0)
  }

  return {
    include,
    cacheInstances,
    cacheCount,
    removeCache,
    removeCacheByPath,
    clearAllCache,
    onRouteChange,
    refreshCacheSnapshot,
  }
}
