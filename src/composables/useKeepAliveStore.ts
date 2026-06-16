import { ref, computed, onMounted, onUpdated, type Component, type VNode, getCurrentInstance } from 'vue'
import { useRouter } from 'vue-router'

/**
 * KeepAlive 缓存管理 Store
 *
 * 核心设计：
 * ──────────────────────────────────────────────
 * Vue 3 KeepAlive 内部维护了 cache: Map<any, VNode>
 * 并挂在 instance.__v_cache 上（dev 模式可用）
 *
 * 本 Store 的 includeList 是"期望缓存名单"，
 * 驱动 <KeepAlive :include> 控制哪些组件被缓存。
 *
 * 同步机制：
 * 1. syncWithVueInternal() — 定期/手动读取 __v_cache，
 *    将 Vue 内部实际缓存与 includeList 做对比，发现不一致则修正
 * 2. 组件 name 错误 / Vue 内部淘汰(max) 等场景都会被捕获
 * ──────────────────────────────────────────────
 */

export interface CacheInstance {
  /** 组件 name（即 KeepAlive cache key） */
  name: string
  /** 对应的路由 path */
  routePath: string
  /** 缓存时间戳 */
  cachedAt: number
  /** 是否为当前活跃实例 */
  isActive: boolean
  /** 数据来源：vue-internal 或 store-expected */
  source: 'vue-internal' | 'store-expected'
}

// ---- 全局单例状态 ----

/** 期望缓存名单 —— 驱动 <KeepAlive :include> */
const includeList = ref<string[]>([])

/** 缓存时间戳（仅 Store 侧记录） */
const cacheTimestamps = ref<Map<string, number>>(new Map())

/** 自动缓存开关（默认开启） */
const autoCacheEnabled = ref(true)

/**
 * 已被用户主动删除的组件 name 集合
 * 删除缓存时记录 → 自动缓存路由切换时跳过 → 用户恢复时移除
 */
const removedSet = ref<Set<string>>(new Set())

/** 路由 path → 组件 name */
const routeNameMap = ref<Map<string, string>>(new Map())

/** 组件 name → 路由 path */
const nameRouteMap = ref<Map<string, string>>(new Map())

/** 组件 name → 显示标签 */
const nameLabelMap = ref<Map<string, string>>(new Map())

/** Vue KeepAlive 内部实际缓存 name 集合（由 syncWithVueInternal 更新） */
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
 * 在 App.vue 的 KeepAlive onVnodeMounted / setup 中调用
 */
export function registerKeepAliveInstance(instance: any) {
  keepAliveInstance = instance
}

/**
 * 从 Vue KeepAlive 内部 __v_cache 读取实际缓存状态
 * 返回当前被缓存的组件 name 集合
 */
function readVueInternalCache(): Set<string> {
  if (!keepAliveInstance) return new Set()

  const cache: Map<any, VNode> | undefined = keepAliveInstance.__v_cache
  if (!cache) return new Set()

  const names = new Set<string>()
  cache.forEach((vnode) => {
    // 从 VNode 中提取组件 name
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
 *
 * 三种场景处理：
 * 1. Vue 内部有但 includeList 没有 → includeList 漏了，补上
 * 2. includeList 有但 Vue 内部没有 → Vue 淘汰/异常，从 includeList 移除
 * 3. 两者一致 → 无操作
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

  // Store 有但 Vue 没有 → 移除
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

  // 更新内部缓存镜像
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
}

/** 导出 nameLabelMap 供外部读取 */
export { nameLabelMap }

// ---- 主要 API ----

export function useKeepAliveStore() {
  const router = useRouter()
  routerInstance = router

  const include = computed(() => includeList.value)
  const isAutoCacheEnabled = computed(() => autoCacheEnabled.value)

  function toggleAutoCache(enabled?: boolean) {
    autoCacheEnabled.value = enabled ?? !autoCacheEnabled.value
  }

  /**
   * 将指定路由的组件加入缓存
   * @param routePath 路由路径
   * @param force 是否强制添加（忽略 removedSet），默认 false
   */
  function addCache(routePath: string, force = false) {
    const compName = getComponentNameByPath(routePath)
    if (!compName) {
      console.warn(`[KeepAliveStore] 无法找到路由 "${routePath}" 对应的组件 name`)
      return
    }
    addCacheByName(compName, force)
  }

  function addCacheByName(compName: string, force = false) {
    if (!force && removedSet.value.has(compName)) return
    if (!includeList.value.includes(compName)) {
      includeList.value.push(compName)
      cacheTimestamps.value.set(compName, Date.now())
    }
    removedSet.value.delete(compName)
  }

  /**
   * 删除指定组件缓存 + 记入 removedSet
   */
  function removeCache(componentName: string) {
    const idx = includeList.value.indexOf(componentName)
    if (idx !== -1) {
      includeList.value.splice(idx, 1)
      cacheTimestamps.value.delete(componentName)
    }
    removedSet.value.add(componentName)
  }

  function removeCacheByPath(routePath: string) {
    const compName = getComponentNameByPath(routePath)
    if (compName) removeCache(compName)
  }

  /**
   * 恢复指定组件缓存
   */
  function restoreCache(componentName: string) {
    removedSet.value.delete(componentName)
    if (!includeList.value.includes(componentName)) {
      includeList.value.push(componentName)
      cacheTimestamps.value.set(componentName, Date.now())
    }
  }

  function restoreAllCache() {
    const toRestore = Array.from(removedSet.value)
    removedSet.value.clear()
    for (const compName of toRestore) {
      if (!includeList.value.includes(compName)) {
        includeList.value.push(compName)
        cacheTimestamps.value.set(compName, Date.now())
      }
    }
  }

  /**
   * 清空所有缓存 + 记入 removedSet
   */
  function clearAllCache() {
    for (const name of includeList.value) {
      removedSet.value.add(name)
    }
    includeList.value.splice(0, includeList.value.length)
    cacheTimestamps.value.clear()
  }

  /**
   * 缓存实例列表（合并 Vue 内部 + Store 期望状态）
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

  const removedInstances = computed<CacheInstance[]>(() => {
    const currentPath = router.currentRoute.value.path
    return Array.from(removedSet.value).map((name) => {
      const routePath = nameRouteMap.value.get(name) ?? ''
      return {
        name,
        routePath,
        cachedAt: 0,
        isActive: routePath === currentPath,
        source: 'store-expected' as const,
      }
    })
  })

  const cacheCount = computed(() => includeList.value.length)
  const removedCount = computed(() => removedSet.value.size)

  /**
   * Vue 内部实际缓存数
   */
  const vueInternalCount = computed(() => vueInternalCacheNames.value.size)

  /**
   * 是否存在不一致（Store 期望 ≠ Vue 实际）
   */
  const isInconsistent = computed(() => {
    if (includeList.value.length !== vueInternalCacheNames.value.size) return true
    for (const name of includeList.value) {
      if (!vueInternalCacheNames.value.has(name)) return true
    }
    return false
  })

  function onRouteChange(path: string) {
    if (!autoCacheEnabled.value) return
    addCache(path, false)
  }

  return {
    include,
    cacheInstances,
    cacheCount,
    removedInstances,
    removedCount,
    isAutoCacheEnabled,
    isInconsistent,
    vueInternalCount,
    addCache,
    addCacheByName,
    removeCache,
    removeCacheByPath,
    restoreCache,
    restoreAllCache,
    clearAllCache,
    toggleAutoCache,
    onRouteChange,
    syncWithVueInternal,
  }
}
