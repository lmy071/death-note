# vue2-vs-vue3-array-reactivity

# Vue 2 vs Vue 3 数组响应式机制对比

## 一句话总结

> Vue 2 改写数组是**做不到**检测 — 技术限制被动补丁；Vue 3 拦截数组方法是**需要精细控制** — 主动优化。
> 

---

## 核心差异

|  | Vue 2 | Vue 3 |
| --- | --- | --- |
| **底层响应式机制** | `Object.defineProperty` | `Proxy` |
| **数组检测能力** | 无法检测索引赋值、`length` 修改、7 个变异方法 | Proxy 原生拦截所有 get/set/has/deleteProperty 等 13 种操作 |
| **是否需要「改写」** | **必须**，否则不响应 | **不需要**，Proxy 天然全覆盖 |
| **改写方式** | 替换 `.__proto__`，重写 7 个方法 | get 陷阱返回包装方法，不改变数组本身 |
| **目的** | 弥补能力缺陷 | 防止死锁、精准追踪、保持引用 |

---

## Vue 2：被动补丁

### 原理

`Object.defineProperty` 只能劫持已有属性的 get/set，无法拦截：

| 操作 | 能被检测？ |
| --- | --- |
| `arr[0] = 'new'` | ❌ 索引赋值无法捕获 |
| `arr.length = 0` | ❌ length 修改无法捕获 |
| `arr.push('x')` | ❌ 方法调用无法捕获 |
| `arr.pop()` | ❌ 同上 |
| `arr.shift()` | ❌ 同上 |
| `arr.unshift('x')` | ❌ 同上 |
| `arr.splice(0, 1)` | ❌ 同上 |
| `arr.sort()` | ❌ 同上 |
| `arr.reverse()` | ❌ 同上 |

### 解决方案：重写原型

```jsx
// Vue 2 源码简化示意
const arrayProto = Array.prototype
const arrayMethods = Object.create(arrayProto)

;['push', 'pop', 'shift', 'unshift', 'splice', 'sort', 'reverse'].forEach(method => {
  const original = arrayProto[method]
  Object.defineProperty(arrayMethods, method, {
    value: function (...args) {
      const result = original.apply(this, args)
      const ob = this.__ob__
      let inserted
      switch (method) {
        case 'push':
        case 'unshift':
          inserted = args
          break
        case 'splice':
          inserted = args.slice(2)
          break
      }
      if (inserted) ob.observeArray(inserted)   // 新元素也要响应式
      ob.dep.notify()                            // 通知更新
      return result
    }
  })
})

// 对响应式数组替换 __proto__
function observe(arr) {
  arr.__proto__ = arrayMethods
}
```

### 缺陷

1. **只能覆盖 7 个方法**，`filter`/`concat`/`slice` 等不触发响应式
2. **索引赋值不响应**：必须用 `$set(arr, index, value)` 或 `arr.splice(index, 1, value)`
3. **无法检测 `length = 0`** 清空
4. **修改了数组原型链**，`console.log(arr.__proto__.__proto__)` 会看到修改痕迹

---

## Vue 3：主动优化

### 原理

`Proxy` 能拦截 **13 种底层操作**，数组的所有行为无需特殊处理就能被检测到：

```jsx
const arr = reactive([1, 2, 3])

arr.push(4)       // ✅ 触发 Proxy set(3, 4) + get(length)
arr[0] = 0        // ✅ 触发 Proxy set(0, 0)
arr.length = 0    // ✅ 触发 Proxy set(length, 0)
arr.splice(1, 1)  // ✅ 触发多次 set + deleteProperty

// 甚至不需要改写的方法也天然响应
arr.concat([4])   // ✅ get(Symbol.isConcatSpreadable) + get(length) + get(0,1,2...)
```

### 但仍做了数组方法拦截（`arrayInstrumentations.ts`）

Vue 3 在 Proxy get 陷阱中返回包装后的数组方法，目的**不是补能力，而是做优化**：

#### 1. 写操作死锁预防 — `push` / `pop` / `shift` / `unshift` / `splice`

```
push 内部执行流程：
  push → 读取 length → Proxy get 陷阱 → track(length)
       → 修改 length → Proxy set 陷阱 → trigger(length)
       → trigger 导致 effect 重新执行 → effect 里再次 push → ... ∞
```

**死锁图示：**

```
┌─────────────────────────────────┐
│  effect()                       │
│    arr.push('x') ───┐           │
│       ↓              │           │
│  get(length) ─── track          │
│       ↓                         │
│  set(length) ─── trigger ───────┘
│       ↑─────────────┘ (无限循环)
└─────────────────────────────────┘
```

**解决方案：**

```jsx
function noTracking(self, method, args = []) {
  pauseTracking()         // 暂停依赖收集
  startBatch()            // 开启批处理（多次 trigger 合并为一次）
  const res = toRaw(self)[method].apply(self, args)
  endBatch()              // 结束批处理 → 触发一次集体更新
  resetTracking()         // 恢复依赖收集
  return res
}
```

#### 2. 身份敏感查找 — `includes` / `indexOf` / `lastIndexOf`

```jsx
const obj = { name: 'test' }
const arr = reactive([obj])

arr.includes(obj)
// ❌ 期望 true，实际 false！
// 原因：arr[0] === Proxy({ name: 'test' })
//        obj    === 原始 { name: 'test' }
//        Proxy(obj) !== obj
```

**解决方案：第一次失败后用 `toRaw` 再查**

```jsx
function searchProxy(self, method, args) {
  const arr = toRaw(self)
  track(arr, TrackOpTypes.ITERATE, ARRAY_ITERATE_KEY)

  const res = arr[method](...args)   // 用原始 args 查找
  if ((res === -1 || res === false) && isProxy(args[0])) {
    args[0] = toRaw(args[0])          // 转 raw 再查一次
    return arr[method](...args)
  }
  return res
}
```

#### 3. 迭代依赖追踪 — `map` / `filter` / `forEach` / `concat` / `join` 等

需要一个统一的 `ARRAY_ITERATE_KEY` 来语义化追踪”数组内容变化”，而非用 `length`：

```
arr.map(x => x.n) 时追踪 → track(arr, ITERATE, ARRAY_ITERATE_KEY)

当数组 push/unshift/splice 等操作时 → trigger(arr, ITERATE, ARRAY_ITERATE_KEY)
→ 所有使用了 map/filter/forEach/... 的 computed 和 watch 重新计算
```

#### 4. 返回值包装

确保派生数组的元素仍然保持响应式：

```jsx
const raw = reactive([{ name: 'a' }])
const result = raw.filter(x => true)
result[0] // → Proxy({ name: 'a' })  而非 { name: 'a' }
```

```jsx
function apply(self, method, fn, thisArg, wrappedRetFn, args) {
  const arr = shallowReadArray(self)
  const result = arr[method].call(arr, wrappedFn, thisArg)
  return needsWrap && wrappedRetFn
    ? wrappedRetFn(result)   // 对结果中每个元素 toWrapped
    : result
}
```

---

## 对比表格

| 维度 | Vue 2 | Vue 3 |
| --- | --- | --- |
| **底层 API** | `Object.defineProperty` | `Proxy` |
| **数组索引读写** | 读 ✅ 写 ❌ | 读 ✅ 写 ✅ |
| **`length` 修改** | ❌ | ✅ |
| **改写方法数量** | 7 个（push/pop/shift/unshift/splice/sort/reverse） | 25 个（几乎所有 Array.prototype 方法） |
| **改写方式** | 替换 `__proto__` | Proxy get 陷阱返回包装函数 |
| **改写目的** | 弥补响应式能力缺口 | 防死锁、精准追踪、保引用 |
| **`arr[0] = x` 响应** | ❌ 需 `$set` | ✅ 直接赋值 |
| **`arr.length = 0`** | ❌ | ✅ |
| **`includes` 正确性** | N/A（不支持 reactive） | ✅ 双次查找（raw → proxy） |
| **push 死锁风险** | ❌ 不存在（defineProperty 不 track get） | ⚠️ 需要 `pauseTracking()` |
| **性能** | 初始化需递归遍历每个属性，数组越大越慢 | Proxy 惰性代理，按需触发 |
| **新增属性** | ❌ | ✅ |

---

## 实际影响

### Vue 2 中的坑（3.x 已消灭）

```jsx
// Vue 2 — 必须记住各种 workaround
const arr = reactive(['a', 'b'])

// ❌ 不工作
arr[0] = 'x'           // 视图不更新
arr.length = 0          // 视图不更新

// ✅ 必须这样
arr.$set(arr, 0, 'x')
arr.splice(0)

// ❌ 不工作
const filtered = arr.filter(x => true)
// filtered 完全不是响应式的
```

```jsx
// Vue 3 — 一切都正常
const arr = reactive(['a', 'b'])

arr[0] = 'x'            // ✅ 更新
arr.length = 0           // ✅ 更新
arr.push('c')            // ✅ 更新（且有批处理合并不重复渲染）

const filtered = computed(() => arr.filter(x => true))
// ✅ filtered.value 自动响应 arr 的变化
```

### 社区常见误解

> “Vue 3 也重写了数组方法，所以和 Vue 2 一样”
> 

**错误。** Vue 3 的数组方法拦截是 Proxy get 陷阱的纯函数返回，不修改原型链：

- Vue 2：`arr.__proto__ = hackedPrototype`（改变了对象）
- Vue 3：`proxy.get = fn → return wrappedMethod`（纯行为代理，对象未变）

验证：

```jsx
const arr = reactive([1, 2, 3])
Object.getPrototypeOf(arr) === Array.prototype  // true（Vue 2 中是 false）
```

---

## 总结

|  | Vue 2 | Vue 3 |
| --- | --- | --- |
| **哲学** | 「做不到，所以要绕过」 | 「能做到，但要做得更好」 |
| **本质** | 缺陷补丁（patch） | 性能优化（optimization） |
| **动机** | 被动 | 主动 |