import { ref, computed, type Component, type VNode } from 'vue'
import { useRouter } from 'vue-router'

/**
 * KeepAlive 缓存管理 Store
 *
 * 策略：全部缓存 + max=7 LRU 淘汰
 * ──────────────────────────────────────────────
 * - 所有已注册页面默认加入 includeList
 * - <KeepAlive :max="7"> 实现 LRU 淘汰
 * - 通过 instance.__v_cache 读取 Vue 内部真实缓存状态
 * - 删除操作：从 include 移除 → Vue 自动销毁缓存实例
 * ──────────────────────────────────────────────
 */

export interface CacheInstance {
  /** 组件 name */
  name: string
  /** 对应的路由 path */
  routePath: string
  /** 缓存时间戳 */
  cachedAt: number
  /** 是否为当前活跃实例 */
  isActive: boolean
  /** 数据来源 */
  source: 'vue-internal' | 'store-expected'
}

// ---- 全局单例状态 ----

/** 缓存名单 —— 驱动 <KeepAlive :include> */
const includeList = ref<string[]>([])

/** 缓存时间戳 */
const cacheTimestamps = ref<Map<string, number>>(new Map())

/** 路由 path → 组件 name */
const routeNameMap = ref<Map<string, string>>(new Map())

/** 组件 name → 路由 path */
const nameRouteMap = ref<Map<string, string>>(new Map())

/** 组件 name → 显示标签 */
const nameLabelMap = ref<Map<string, string>>(new Map())

/** Vue KeepAlive 内部实际缓存 name 集合 */
const vueInternalCacheNames = ref<Set<string>>(new Set())

/** KeepAlive 组件实例引用 */
let keepAliveInstance: any = null

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
 * 从 Vue KeepAlive 内部 __v_cache 读取实际缓存状态
 */
function readVueInternalCache(): Set<string> {
  if (!keepAliveInstance) return new Set()

  const cache: Map<any, VNode> | undefined = keepAliveInstance.__v_cache
  if (!cache) return new Set()

  const names = new Set<string>()
  cache.forEach((vnode) => {
    const comp = vnode.type
    if (comp && typeof comp === 'object' && 'name' in comp) {
      const name = (comp as any).name
      if (typeof name === 'string') {
        names.add(name)
      }
    }
  })
  return names
}

/**
 * 同步 Store 的 includeList 与 Vue 内部缓存
 */
export function syncWithVueInternal(): { added: string[]; removed: string[] } {
  const actualNames = readVueInternalCache()
  const expectedNames = new Set(includeList.value)

  const added: string[] = []
  const removed: string[] = []

  // Vue 有但 Store 没有 → 补上
  for (const name of actualNames) {
    if (!expectedNames.has(name)) {
      includeList.value.push(name)
      if (!cacheTimestamps.value.has(name)) {
        cacheTimestamps.value.set(name, Date.now())
      }
      added.push(name)
    }
  }

  // Store 有但 Vue 没有 → 移除（LRU 淘汰等）
  for (const name of expectedNames) {
    if (!actualNames.has(name)) {
      const idx = includeList.value.indexOf(name)
      if (idx !== -1) {
        includeList.value.splice(idx, 1)
      }
      cacheTimestamps.value.delete(name)
      removed.push(name)
    }
  }

  vueInternalCacheNames.value = actualNames
  return { added, removed }
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
  // 默认全部加入缓存名单
  if (!includeList.value.includes(componentName)) {
    includeList.value.push(componentName)
    cacheTimestamps.value.set(componentName, Date.now())
  }
}

/** 导出 nameLabelMap */
export { nameLabelMap }

// ---- 主要 API ----

export function useKeepAliveStore() {
  const router = useRouter()
  routerInstance = router

  const include = computed(() => includeList.value)

  /**
   * 将指定路由的组件加入缓存
   */
  function addCache(routePath: string) {
    const compName = getComponentNameByPath(routePath)
    if (!compName) {
      console.warn(`[KeepAliveStore] 无法找到路由 "${routePath}" 对应的组件 name`)
      return
    }
    if (!includeList.value.includes(compName)) {
      includeList.value.push(compName)
      cacheTimestamps.value.set(compName, Date.now())
    }
  }

  /**
   * 删除指定组件缓存
   * 从 include 列表移除 → Vue KeepAlive 自动销毁对应缓存实例
   */
  function removeCache(componentName: string) {
    const idx = includeList.value.indexOf(componentName)
    if (idx !== -1) {
      includeList.value.splice(idx, 1)
      cacheTimestamps.value.delete(componentName)
    }
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
    cacheTimestamps.value.clear()
  }

  /**
   * 缓存实例列表
   */
  const cacheInstances = computed<CacheInstance[]>(() => {
    const currentPath = router.currentRoute.value.path
    const actualNames = vueInternalCacheNames.value

    return includeList.value.map((name) => {
      const routePath = nameRouteMap.value.get(name) ?? ''
      return {
        name,
        routePath,
        cachedAt: cacheTimestamps.value.get(name) ?? 0,
        isActive: routePath === currentPath,
        source: actualNames.has(name) ? 'vue-internal' as const : 'store-expected' as const,
      }
    })
  })

  const cacheCount = computed(() => includeList.value.length)
  const vueInternalCount = computed(() => vueInternalCacheNames.value.size)

  /**
   * 是否存在不一致
   */
  const isInconsistent = computed(() => {
    if (includeList.value.length !== vueInternalCacheNames.value.size) return true
    for (const name of includeList.value) {
      if (!vueInternalCacheNames.value.has(name)) return true
    }
    return false
  })

  function onRouteChange(path: string) {
    addCache(path)
  }

  return {
    include,
    cacheInstances,
    cacheCount,
    isInconsistent,
    vueInternalCount,
    addCache,
    removeCache,
    removeCacheByPath,
    clearAllCache,
    onRouteChange,
    syncWithVueInternal,
  }
}
