# Vue3 Watch 源码解析

# Vue3 Watch 源码解析

> 基于 Vue 3.5+ 源码，`watch` 的核心逻辑分为两层：
> 

> - **`@vue/reactivity` 包**：`packages/reactivity/src/watch.ts` — 底层 `watch` 实现
> 

> - **`@vue/runtime-core` 包**：`packages/runtime-core/src/apiWatch.ts` — 组件级 `doWatch`，处理调度策略和 SSR
> 

---

## 一、整体架构

```
用户调用
  │
  ├─ watchEffect(cb)          ─┐
  ├─ watchPostEffect(cb)       │  统一入口
  ├─ watchSyncEffect(cb)       │
  └─ watch(source, cb, opts)  ─┘
        │
        ▼
  doWatch(source, cb, options)     ← runtime-core 层
        │
        │  构建 scheduler / augmentJob
        │  处理 flush: pre / post / sync
        │
        ▼
  baseWatch(source, cb, opts)      ← reactivity 层
        │
        │  构建 getter / ReactiveEffect / job
        │  执行初始运行
        │
        ▼
  返回 WatchHandle { stop, pause, resume }
```

---

## 二、runtime-core 层：doWatch

### 2.1 入口函数

```tsx
// apiWatch.ts
function doWatch(
  source: WatchSource | WatchSource[] | WatchEffect | object,
  cb: WatchCallback | null,
  options: WatchOptions = EMPTY_OBJ,
): WatchHandle {
  const { immediate, deep, flush, once } = options
  // ...
}
```

`doWatch` 是所有 watch API 的统一实现入口：

| API | cb 参数 | flush |
| --- | --- | --- |
| `watchEffect` | `null` | 默认 `pre` |
| `watchPostEffect` | `null` | `post` |
| `watchSyncEffect` | `null` | `sync` |
| `watch` | 用户传入 | 用户指定，默认 `pre` |

### 2.2 调度策略（flush）

`doWatch` 最重要的职责是**根据 flush 选项构建 scheduler**：

```tsx
let isPre = false

if (flush === 'post') {
  // post: 回调在 DOM 更新后执行
  baseWatchOptions.scheduler = job => {
    queuePostRenderEffect(job, instance?.suspense)
  }
} else if (flush !== 'sync') {
  // 默认 pre: 回调在 DOM 更新前执行
  isPre = true
  baseWatchOptions.scheduler = (job, isFirstRun) => {
    if (isFirstRun) {
      job()  // 首次运行立即执行
    } else {
      queueJob(job)  // 后续运行加入调度队列
    }
  }
}
// flush === 'sync' 时不设置 scheduler，即同步执行
```

三种 flush 的时序：

```
响应式数据变化
    │
    ├─ sync  → 立即执行回调
    │
    ├─ pre   → 加入 queueJob，在组件更新前执行
    │
    └─ post  → 加入 queuePostRenderEffect，在组件更新后执行
```

### 2.3 augmentJob：标记调度属性

```tsx
baseWatchOptions.augmentJob = (job: SchedulerJob) => {
  if (cb) {
    job.flags |= SchedulerJobFlags.ALLOW_RECURSE  // 允许自触发
  }
  if (isPre) {
    job.flags |= SchedulerJobFlags.PRE  // 标记为 pre 任务
    if (instance) {
      job.id = instance.uid  // 绑定组件实例
      job.i = instance
    }
  }
}
```

**关键细节**：

- `ALLOW_RECURSE`：允许 watcher 回调中修改被监听的源，触发自身重新执行（#1727 修复）
- `PRE` 标记 + `instance.uid`：确保同一组件的 pre watcher 按组件顺序执行

### 2.4 SSR 处理

```tsx
if (__SSR__ && isInSSRComponentSetup) {
  if (flush === 'sync') {
    // sync 模式收集 watcher handles，服务端渲染完统一停止
    ssrCleanup = ctx.__watcherHandles || (ctx.__watcherHandles = [])
  } else if (!runsImmediately) {
    // 非 immediate 的非 sync watcher 在 SSR 中直接返回空 handle
    // 因为不会有后续触发
    return dummyHandle
  }
}
```

---

## 三、reactivity 层：baseWatch

### 3.1 源类型判断与 getter 构建

`baseWatch` 的第一步是根据 `source` 的类型构建 `getter`：

```tsx
if (isRef(source)) {
  getter = () => source.value
  forceTrigger = isShallow(source)

} else if (isReactive(source)) {
  getter = () => reactiveGetter(source)
  forceTrigger = true

} else if (isArray(source)) {
  isMultiSource = true
  forceTrigger = source.some(s => isReactive(s) || isShallow(s))
  getter = () => source.map(s => {
    if (isRef(s)) return s.value
    else if (isReactive(s)) return reactiveGetter(s)
    else if (isFunction(s)) return s()
  })

} else if (isFunction(source)) {
  if (cb) {
    // watch(source, cb) — source 作为 getter
    getter = source
  } else {
    // watchEffect — source 作为 effect，需要处理 cleanup
    getter = () => {
      if (cleanup) { pauseTracking(); cleanup(); resetTracking() }
      const prev = activeWatcher
      activeWatcher = effect
      try { return source(boundCleanup) }
      finally { activeWatcher = prev }
    }
  }
}
```

**核心逻辑**：

| source 类型 | getter 行为 | forceTrigger |
| --- | --- | --- |
| `Ref` | `() => source.value` | ShallowRef → true |
| `Reactive` | `() => reactiveGetter(source)` | true |
| `Array` | 遍历每个元素按类型取值 | 任一 reactive/shallow → true |
| `Function`（有 cb） | source 本身作为 getter | false |
| `Function`（无 cb） | 执行 source 并管理 cleanup | false |

### 3.2 reactiveGetter 与 deep

```tsx
const reactiveGetter = (source: object) => {
  if (deep) return source  // deep 模式在下面统一 traverse
  // deep: false/0 或 shallow reactive → 只遍历一层
  if (isShallow(source) || deep === false || deep === 0)
    return traverse(source, 1)
  // deep 未设置 + reactive 对象 → 深度遍历
  return traverse(source)
}
```

> 💡 **关键理解**：监听 reactive 对象时，`deep` 默认为 `undefined`，此时会自动深度遍历。只有显式设置 `deep: false` 才会只监听浅层变化。
> 

### 3.3 deep + cb 的 traverse 包装

```tsx
if (cb && deep) {
  const baseGetter = getter
  const depth = deep === true ? Infinity : deep  // deep: 2 → 只遍历 2 层
  getter = () => traverse(baseGetter(), depth)
}
```

`deep` 选项支持数字：`deep: 2` 表示只遍历 2 层深度，比 `deep: true`（无限深度）更精细控制。

### 3.4 ReactiveEffect 创建

```tsx
effect = new ReactiveEffect(getter)

effect.scheduler = scheduler
  ? () => scheduler(job, false)
  : job

boundCleanup = fn => onWatcherCleanup(fn, false, effect)

cleanup = effect.onStop = () => {
  const cleanups = cleanupMap.get(effect)
  if (cleanups) {
    for (const cleanup of cleanups) cleanup()
    cleanupMap.delete(effect)
  }
}
```

**核心机制**：

- `ReactiveEffect` 是 Vue 响应式系统的副作用基类
- `getter` 执行时访问响应式数据 → 自动收集依赖
- 依赖变化时 → 触发 `effect.scheduler` → 调度 `job` 执行

### 3.5 job：回调执行的核心逻辑

```tsx
const job = (immediateFirstRun?: boolean) => {
  // 如果 effect 不活跃或没变脏，跳过
  if (!(effect.flags & EffectFlags.ACTIVE) || (!effect.dirty && !immediateFirstRun)) {
    return
  }

  if (cb) {
    // watch(source, cb) 模式
    const newValue = effect.run()

    if (
      deep ||
      forceTrigger ||
      (isMultiSource
        ? newValue.some((v, i) => hasChanged(v, oldValue[i]))
        : hasChanged(newValue, oldValue))
    ) {
      // 先执行上一次的 cleanup
      if (cleanup) cleanup()

      const currentWatcher = activeWatcher
      activeWatcher = effect
      try {
        const args = [newValue, oldValue === INITIAL_WATCHER_VALUE ? undefined : oldValue, boundCleanup]
        oldValue = newValue
        cb(...args)
      } finally {
        activeWatcher = currentWatcher
      }
    }
  } else {
    // watchEffect 模式 — 直接重新执行 effect
    effect.run()
  }
}
```

**关键流程**：

```
依赖变化 → scheduler 调度 job
    │
    ├─ 检查 effect 是否活跃 (ACTIVE flag)
    ├─ 检查 effect.dirty 或 immediateFirstRun
    │
    ├─ effect.run() → 重新执行 getter → 得到 newValue
    │
    ├─ 判断是否需要触发回调：
    │   ├─ deep → 总是触发（因为 traverse 了所有属性）
    │   ├─ forceTrigger → reactive/shallow 总是触发
    │   └─ hasChanged → 用 Object.is 判断值是否变化
    │
    ├─ 执行旧 cleanup
    ├─ 设置 activeWatcher = effect（供 onWatcherCleanup 注册）
    ├─ 执行 cb(newValue, oldValue, onCleanup)
    └─ 更新 oldValue = newValue
```

### 3.6 初始运行

```tsx
if (cb) {
  if (immediate) {
    job(true)          // 立即执行回调
  } else {
    oldValue = effect.run()  // 只收集依赖，不执行回调
  }
} else {
  // watchEffect
  effect.run()  // 立即执行
}
```

---

## 四、traverse：深度遍历

```tsx
export function traverse(
  value: unknown,
  depth: number = Infinity,
  seen?: Map<unknown, number>,
): unknown {
  if (depth <= 0 || !isObject(value) || value[ReactiveFlags.SKIP]) {
    return value
  }

  seen = seen || new Map()
  if ((seen.get(value) || 0) >= depth) return value  // 防止循环引用

  seen.set(value, depth)
  depth--

  if (isRef(value)) {
    traverse(value.value, depth, seen)
  } else if (isArray(value)) {
    for (let i = 0; i < value.length; i++) {
      traverse(value[i], depth, seen)
    }
  } else if (isSet(value) || isMap(value)) {
    value.forEach(v => traverse(v, depth, seen))
  } else if (isPlainObject(value)) {
    for (const key in value) {
      traverse(value[key], depth, seen)
    }
    for (const key of Object.getOwnPropertySymbols(value)) {
      if (Object.prototype.propertyIsEnumerable.call(value, key)) {
        traverse(value[key], depth, seen)
      }
    }
  }
  return value
}
```

**traverse 的作用**：访问对象的每个属性 → 触发 getter → 收集依赖。这样当对象任意深层属性变化时，都能触发 watcher。

**性能优化**：

- `seen` Map 防止循环引用导致的无限递归
- `depth` 参数控制遍历深度（`deep: 2` 只遍历 2 层）
- 跳过 `__v_skip` 标记的对象

---

## 五、WatchHandle：暂停、恢复、停止

```tsx
const watchHandle: WatchHandle = () => {
  effect.stop()
  if (scope && scope.active) {
    remove(scope.effects, effect)
  }
}

watchHandle.pause = effect.pause.bind(effect)
watchHandle.resume = effect.resume.bind(effect)
watchHandle.stop = watchHandle
```

Vue 3.5+ 返回 `WatchHandle` 对象（不再只是 `WatchStopHandle` 函数）：

| 方法 | 作用 |
| --- | --- |
| `watchHandle()` / `watchHandle.stop()` | 停止 watcher，清理所有副作用 |
| `watchHandle.pause()` | 暂停 watcher，不响应变化但保留依赖 |
| `watchHandle.resume()` | 恢复 watcher，重新开始响应变化 |

---

## 六、once 选项的实现

```tsx
if (once && cb) {
  const _cb = cb
  cb = (...args) => {
    _cb(...args)
    watchHandle()  // 执行一次后自动停止
  }
}
```

非常简洁：包装原始回调，执行一次后自动调用 `watchHandle()` 停止 watcher。

---

## 七、cleanup 机制

### 7.1 注册 cleanup

```tsx
// 用户侧
watch(id, (newVal, oldVal, onCleanup) => {
  const controller = new AbortController()
  fetch(`/api/${newVal}`, { signal: controller.signal })
  onCleanup(() => controller.abort())  // 注册清理函数
})

// 内部实现
const cleanupMap: WeakMap<ReactiveEffect, (() => void)[]> = new WeakMap()

export function onWatcherCleanup(
  cleanupFn: () => void,
  failSilently = false,
  owner: ReactiveEffect | undefined = activeWatcher,
): void {
  if (owner) {
    let cleanups = cleanupMap.get(owner)
    if (!cleanups) cleanupMap.set(owner, (cleanups = []))
    cleanups.push(cleanupFn)
  }
}
```

### 7.2 cleanup 执行时机

```
1. watcher 回调再次执行前 → 执行上一次注册的 cleanup
2. watcher 停止时（effect.onStop） → 执行所有 cleanup
```

---

## 八、instanceWatch：this.$watch

```tsx
export function instanceWatch(
  this: ComponentInternalInstance,
  source: string | Function,
  value: WatchCallback | ObjectWatchOptionItem,
  options?: WatchOptions,
): WatchHandle {
  const publicThis = this.proxy
  const getter = isString(source)
    ? source.includes('.')
      ? createPathGetter(publicThis!, source)  // 'a.b.c' → () => this.a.b.c
      : () => publicThis![source]               // 'a' → () => this.a
    : source.bind(publicThis, publicThis)

  let cb = isFunction(value) ? value : value.handler
  const reset = setCurrentInstance(this)
  const res = doWatch(getter, cb.bind(publicThis), options)
  reset()
  return res
}
```

**`this.$watch` 支持点路径**：`this.$watch('a.b.c', cb)` 会自动创建路径 getter。

---

## 九、完整执行流程图

```
watch(count, (newVal, oldVal) => { ... }, { immediate: true })
    │
    ▼
doWatch()
    ├─ 构建 scheduler（flush: 'pre'）
    ├─ 构建 augmentJob（ALLOW_RECURSE + PRE 标记）
    │
    ▼
baseWatch()
    ├─ 判断 source 类型 → 构建 getter
    │   count 是 Ref → getter = () => count.value
    │
    ├─ deep 选项处理 → 无 deep → 不 traverse
    │
    ├─ 创建 ReactiveEffect(getter)
    ├─ effect.scheduler = () => scheduler(job, false)
    │
    ├─ 初始运行（immediate: true）
    │   └─ job(true) → effect.run() → newValue = 0
    │      └─ cb(0, undefined, onCleanup)  ← 首次执行回调
    │
    └─ 返回 WatchHandle
         │
         │  count.value = 1  ← 响应式数据变化
         │
         ▼
    effect.trigger()
         │
         ▼
    scheduler(job, false)
         │
         ▼
    queueJob(job)   ← 加入 pre 队列
         │
         ▼
    job()
         ├─ effect.run() → newValue = 1
         ├─ hasChanged(1, 0) → true
         ├─ 执行 cleanup（如有）
         ├─ cb(1, 0, onCleanup)  ← 执行用户回调
         └─ oldValue = 1
```

---

## 十、关键设计总结

| 设计点 | 实现方式 | 为什么这样做 |
| --- | --- | --- |
| 两层架构 | reactivity 层 + runtime-core 层 | 解耦：底层可独立使用，上层处理组件调度 |
| scheduler 抽象 | `WatchScheduler = (job, isFirstRun) => void` | 同一 watch 逻辑，不同调度策略 |
| traverse 深度控制 | `depth` 参数 + `seen` Map 循环检测 | 性能优化：避免遍历过深或循环引用 |
| forceTrigger | reactive 对象强制触发 | 对象引用不变但内部属性可能变了，必须触发 |
| ALLOW_RECURSE | job flags 标记 | 允许 watcher 回调修改被监听的源（如防抖场景） |
| cleanup WeakMap | `WeakMap<ReactiveEffect, (() => void)[]>` | 自动垃圾回收：effect 被销毁时 cleanup 也自动释放 |
| once 包装 | 包装 cb 执行后调用 stop | 最简实现，不需要额外状态 |
| pause/resume | 委托给 ReactiveEffect | 停止依赖追踪但保留关系，恢复时无需重新收集 |

---

## 十一、常见问题源码级解答

### Q1：为什么监听 reactive 对象不需要手动加 deep？

因为 `reactiveGetter` 在 `deep` 为 `undefined` 时会调用 `traverse(source)` 深度遍历所有属性，等效于自动 `deep: true`。

### Q2：watch 和 watchEffect 的源码区别？

- `watch` 传了 `cb` → job 中 `effect.run()` 取新值，判断 `hasChanged` 后才执行回调
- `watchEffect` 没传 `cb` → job 中直接 `effect.run()` 重新执行 effect 函数

### Q3：为什么 deep: number 有用？

`traverse(value, depth)` 中的 `depth` 参数控制递归深度。对于大型嵌套对象，`deep: 2` 只遍历 2 层，比 `deep: true`（`Infinity`）性能好得多。

### Q4：oldValue 为什么第一次是 undefined？

```tsx
oldValue === INITIAL_WATCHER_VALUE ? undefined : oldValue
```

`INITIAL_WATCHER_VALUE = {}` 是一个哨兵值，只在首次运行时使用。当 `immediate: true` 时，`oldValue` 初始为哨兵值，传给用户时替换为 `undefined`。

### Q5：onCleanup 的 cleanup 什么时候执行？

1. **回调再次执行前**：`job()` 中 `if (cleanup) cleanup()` — 先清理上次副作用
2. **watcher 停止时**：`effect.onStop` — 清理所有注册的 cleanup 函数

---

> 👀 *读懂 Vue3 的 watch，关键是理解 ReactiveEffect + scheduler 的双轨设计：Effect 负责依赖收集和触发，scheduler 负责调度策略（何时执行）。watch 的所有功能——immediate、deep、flush、once、cleanup——都是在这两条轨道上搭建的。*
>