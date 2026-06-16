import { ref, computed, type Component } from 'vue'
import { useRouter } from 'vue-router'

/**
 * KeepAlive 缓存管理 Store
 *
 * 职责：
 * 1. 维护 include 列表，控制 <KeepAlive> 缓存哪些组件
 * 2. 提供读取当前缓存实例的 API
 * 3. 提供删除指定缓存实例的 API（删除后不会被自动缓存加回，除非用户主动恢复）
 * 4. 支持自动缓存开关 & 已删除记忆
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
}

/** 所有可缓存页面的注册信息 */
export interface CacheablePage {
  routePath: string
  componentName: string
  label: string
}

// ---- 全局单例状态 ----
const includeList = ref<string[]>([])
const cacheTimestamps = ref<Map<string, number>>(new Map())

/** 自动缓存开关（默认开启） */
const autoCacheEnabled = ref(true)

/**
 * 已被用户主动删除的组件 name 集合
 * - 删除缓存时记录到此处
 * - 自动缓存路由切换时跳过此集合中的组件
 * - 用户在管理器中主动恢复缓存时从此集合移除
 */
const removedSet = ref<Set<string>>(new Set())

/** 路由 path → 组件 name 映射（初始化时填充） */
const routeNameMap = ref<Map<string, string>>(new Map())

/** 组件 name → 路由 path 反向映射 */
const nameRouteMap = ref<Map<string, string>>(new Map())

/** 组件 name → 显示标签映射 */
const nameLabelMap = ref<Map<string, string>>(new Map())

let routerInstance: ReturnType<typeof useRouter> | null = null

/**
 * 初始化：注册路由与组件 name 的映射
 * 必须在 setup 中调用一次
 */
export function initKeepAliveStore() {
  const router = useRouter()
  routerInstance = router

  // 从路由记录中提取 path → component name 映射
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
 * 通过路由 path 获取组件 name
 */
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

/**
 * 手动注册 path → componentName 映射
 * 用于自动推断失败时的兜底
 */
export function registerRouteNameMapping(path: string, componentName: string, label?: string) {
  routeNameMap.value.set(path, componentName)
  nameRouteMap.value.set(componentName, path)
  if (label) {
    nameLabelMap.value.set(componentName, label)
  }
}

/** 导出 nameLabelMap 供外部读取 */
export { nameLabelMap }

export function useKeepAliveStore() {
  const router = useRouter()
  routerInstance = router

  /** 当前 KeepAlive 的 include 列表 */
  const include = computed(() => includeList.value)

  /** 自动缓存开关状态 */
  const isAutoCacheEnabled = computed(() => autoCacheEnabled.value)

  /**
   * 切换自动缓存开关
   */
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

  /**
   * 通过组件 name 添加缓存
   */
  function addCacheByName(compName: string, force = false) {
    // 如果组件在已删除集合中且非强制，则跳过
    if (!force && removedSet.value.has(compName)) {
      return
    }
    if (!includeList.value.includes(compName)) {
      includeList.value.push(compName)
      cacheTimestamps.value.set(compName, Date.now())
    }
    // 添加缓存时从已删除集合移除（用户主动恢复）
    removedSet.value.delete(compName)
  }

  /**
   * 删除指定组件 name 的缓存实例
   * 同时记入 removedSet，防止自动缓存加回
   */
  function removeCache(componentName: string) {
    const idx = includeList.value.indexOf(componentName)
    if (idx !== -1) {
      includeList.value.splice(idx, 1)
      cacheTimestamps.value.delete(componentName)
    }
    // 记录为主动删除
    removedSet.value.add(componentName)
  }

  /**
   * 通过路由 path 删除缓存
   */
  function removeCacheByPath(routePath: string) {
    const compName = getComponentNameByPath(routePath)
    if (compName) {
      removeCache(compName)
    }
  }

  /**
   * 恢复指定组件的缓存（从 removedSet 中移除并加入 include）
   */
  function restoreCache(componentName: string) {
    removedSet.value.delete(componentName)
    if (!includeList.value.includes(componentName)) {
      includeList.value.push(componentName)
      cacheTimestamps.value.set(componentName, Date.now())
    }
  }

  /**
   * 恢复所有已删除的缓存
   */
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
   * 清空所有缓存
   * 同时将所有已缓存的组件记入 removedSet
   */
  function clearAllCache() {
    for (const name of includeList.value) {
      removedSet.value.add(name)
    }
    includeList.value.splice(0, includeList.value.length)
    cacheTimestamps.value.clear()
  }

  /**
   * 获取当前所有缓存实例信息
   */
  const cacheInstances = computed<CacheInstance[]>(() => {
    const currentPath = router.currentRoute.value.path
    return includeList.value.map((name) => {
      const routePath = nameRouteMap.value.get(name) ?? ''
      return {
        name,
        routePath,
        cachedAt: cacheTimestamps.value.get(name) ?? 0,
        isActive: routePath === currentPath,
      }
    })
  })

  /**
   * 获取所有被主动删除（不再自动缓存）的组件信息
   */
  const removedInstances = computed<CacheInstance[]>(() => {
    const currentPath = router.currentRoute.value.path
    return Array.from(removedSet.value).map((name) => {
      const routePath = nameRouteMap.value.get(name) ?? ''
      return {
        name,
        routePath,
        cachedAt: 0,
        isActive: routePath === currentPath,
      }
    })
  })

  /**
   * 缓存数量
   */
  const cacheCount = computed(() => includeList.value.length)

  /**
   * 已删除数量
   */
  const removedCount = computed(() => removedSet.value.size)

  /**
   * 路由切换时自动缓存（供 App.vue watch 调用）
   * 仅在 autoCacheEnabled 且组件不在 removedSet 时生效
   */
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
    addCache,
    addCacheByName,
    removeCache,
    removeCacheByPath,
    restoreCache,
    restoreAllCache,
    clearAllCache,
    toggleAutoCache,
    onRouteChange,
  }
}
