# ref和reactive的区别

## 一、核心原理：从同一个响应式引擎出发

Vue 3 的响应式系统只有一个底层实现 —— Proxy。无论是 ref 还是 reactive，最终都依赖相同的 Proxy Handler：reactiveHandler / readonlyHandler / shallowReactiveHandler。ref 本质上是一个「壳」：把任意值包进一个带有 .value 的对象，再用 reactive() 把这个壳变成响应式的。

```tsx
// reactive 源码（packages/reactivity/src/reactive.ts）
export function reactive<T extends object>(target: T): T {
  // 防止重复代理：如果 target 已经是代理，直接返回
  if (target && (target as Target).__v_isReactive) {
    return target as T
  }
  return new Proxy(target, reactiveHandler)
}

// ref 源码（packages/reactivity/src/ref.ts）
export function ref<T>(value: T): Ref<UnwrapRef<T>> {
  return createRef(value, false)
}

function createRef(raw: unknown, shallow: boolean) {
  if (isRef(raw)) {
    return raw  // 已经是 ref，直接返回
  }
  return new RefImpl(raw, shallow)
}

// 核心类
class RefImpl<T> {
  private _value: T

  constructor(private rawValue: T, private shallow: boolean) {
    // 关键：数组/对象走 reactive，基础类型保持原样
    this._value = shallow ? rawValue : convert(raw)
  }

  get value() {
    // 每次 .value 访问，手动触发依赖收集
    trackRefValue(this)
    return this._value
  }

  set value(newVal) {
    if (hasChanged(newVal, this.rawValue)) {
      this.rawValue = newVal
      this._value = this.shallow ? newVal : convert(newVal)
      // 手动触发更新
      triggerRefValue(this, 'set')
    }
  }
}

// convert 决定 shallow vs deep
function convert<T>(value: T): T {
  return isObject(value) ? reactive(value) : value
}
```

## 二、依赖收集时机：.value 是关键分界线

reactive 在 Proxy get trap 中直接触发依赖收集；ref 在 get value() 中手动调用 trackRefValue()。两者的触发位置不同，导致了使用上的差异。

### reactive：属性访问 → Proxy get trap → track()

```tsx
// packages/reactivity/src/baseHandlers.ts
const reactiveHandler: ProxyHandler<Record<string, any>> = {
  get(target, key, receiver) {
    const res = Reflect.get(target, key, receiver)

    // 关键：每个属性的 get 都会触发 track
    // 依赖的 key 是 (target, key) 组合
    track(target, 'get', key)

    // 如果是对象，递归返回响应式（实现深度响应式）
    if (isObject(res)) {
      return reactive(res)
    }
    return res
  },

  set(target, key, value, receiver) {
    const oldValue = target[key]
    const result = Reflect.set(target, key, value, receiver)

    if (hasChanged(value, oldValue)) {
      // 精确到 key 级别的触发
      trigger(target, 'set', key, value, oldValue)
    }
    return result
  }
}
```

### ref：.value 读取 → get value() → trackRefValue()

```tsx
// RefImpl 的 get value()
get value() {
  // 每次 .value 访问，都手动触发依赖收集
  trackRefValue(this)  // → track({}.__v_ref, 'get', 'value')
  return this._value
}

// 核心区别：
// 1. ref 只收集 {}.__v_ref 上的 'value' 这个 key 的依赖
//    不管你读的是 ref.value.count 还是 ref.value.name，
//    依赖收集的 key 永远是 'value'
// 2. reactive 精确到每个属性 key

// 这就是为什么：
const r = reactive({ count: 0, name: 'foo' })
// r.count 变化 → 只触发依赖了 count 的 effect
// r.name 变化 → 只触发依赖了 name 的 effect

const c = ref({ count: 0, name: 'foo' })
// c.value.count 变化 → 触发所有依赖 c.value 的 effect（粗粒度）
// c.value = { count: 1 }  → 整个 c.value 的依赖全部触发
```

## 三、对象解构：reactive 的致命陷阱

reactive 对象解构后，失去响应式连接。这是 reactive 最常踩的坑，ref 不存在这个问题。

```tsx
// ❌ reactive 解构 —— 失去响应式
const state = reactive({ count: 0 })
const { count } = state
// count 现在是普通 number，脱离了 Proxy 代理
console.log(count)   // 0（读的是原始值，不是代理）
count++              // ❌ 不生效！修改的是解构出的局部变量
state.count++        // ✅ 正确做法

// ✅ 正确：用 toRefs 保持响应式
const state = reactive({ count: 0 })
const { count } = toRefs(state)
// count 现在是 Ref<number>
count.value++        // ✅ 相当于 state.count++
toRefs(state).count.value++

// ✅ ref 解构 —— 不存在这个问题
const count = ref(0)
// count 本身就是 Ref 对象，天然保持响应式

// 源码证据：reactiveHandler get trap 中
// packages/reactivity/src/baseHandlers.ts
get(target, key, receiver) {
  const res = Reflect.get(target, key, receiver)
  track(target, 'get', key)
  // 如果访问的属性值本身是 ref，不递归，返回它本身
  if (isRef(res)) {
    return res
  }
  if (isObject(res)) {
    return reactive(res)
  }
  return res
}
// 因此：reactive({ count: ref(0) }).count 仍然是 ref，不需要 .value
```

## 四、数组访问：Proxy 劫持 vs .value

```tsx
// reactive 数组：Proxy 自动劫持所有操作
const arr = reactive([1, 2, 3])
arr[0] = 10             // ✅ Proxy set trap 拦截
arr.push(4)            // ✅ 拦截（push 内部会访问 length）
arr.filter(n => n > 1) // ✅ Proxy get trap 拦截所有方法

// ref 数组：必须通过 .value
const arrRef = ref([1, 2, 3])
arrRef.value[0] = 10    // ✅ 修改数组内容（_value 被修改）
arrRef.value = [10,2,3] // ✅ 整体替换（triggerRefValue 触发更新）
arrRef.value.push(4)    // ✅ push 返回新 length

// 注意 ref 数组的陷阱：
// const arr = ref([1,2,3])
// arr.value[0] = 99
// 这修改了数组内容，但由于 _value 本身是 reactive 数组，
// 所以能正确触发依赖更新（通过 Proxy 拦截）
// 但注意 trigger 的是 'set' 在数组元素上的依赖，
// 不是 ref 本身的 value 依赖表

// reactive 和 ref 在数组场景下的行为对比：
// reactive: arr[0] 变化触发 '0' key 的 effect
// ref:      arr.value[0] = x 触发 reactive 数组的 '0' key effect
//           arr.value = newArr 触发 ref 的 value effect
```

## 五、TypeScript 类型推导：ref 更安全

```tsx
// ref<T> 的类型推导
const count = ref(0)           // Ref<number>
const name = ref('foo')        // Ref<string>
const obj = ref({ a: 1 })     // Ref<{ a: number }>

// 读取时必须 .value —— TS 类型安全
count.value = 'hello'          // ❌ Type 'string' is not assignable

// reactive 的类型推导
const state = reactive({ count: 0, name: 'foo' })
state.count = 'hello'          // ❌ TS 报错

// 但 reactive 有陷阱：
const arr = reactive([])       // never[]，类型丢失
const arr = reactive<number[]>([])  // ✅ 必须手动指定泛型

// ref 的 isRef 类型守卫
function isRef<T>(r: any): r is Ref<T>

// unref：自动去掉 .value
function unref<T>(ref: Ref<T> | T): T {
  return isRef(ref) ? ref.value : ref
}

// Ref 接口定义
interface Ref<T> {
  value: T
}

// 模板 ref 的类型推导（compiler 介入）
// <div ref="el">  → 推断 el: Ref<HTMLElement | null>
// <div :ref="el"> → 推断 el: (el: HTMLElement) => void
declare module '@vue/runtime-dom' {
  interface HTMLAttributes {
    ref?: Ref<HTMLElement | null> | string | ((el: any) => void)
  }
}
```

## 六、响应式替换（整体赋值）的差异

```tsx
// reactive：变量本身就是对象引用，可以直接替换
let state = reactive({ count: 0 })
state = reactive({ count: 1 })  // ✅ 直接替换引用

// 陷阱：不能通过函数参数替换
function resetReactive() {
  state = reactive({ count: 0 })  // ❌ 改不了外部 state
}
// 必须通过代理操作：
function resetReactive() {
  state.count = 0  // ✅
}

// ref：可以整体替换，也可以 .value 修改
let count = ref(0)
count.value = 1            // ✅ 修改内部值
count = ref(2)             // ✅ 替换整个 ref 对象

// ref 的函数参数替换：
function resetRef() {
  count.value = 0  // ✅ 写入 RefImpl 的 _value
}
// 或者整个 ref 替换（变量本身可以被修改）：
function resetRef() {
  count = ref(0)  // ✅ 替换了外部变量（ref 本身是 JS 变量）
```

## 七、性能：依赖收集粒度的差异

从实现看，两者性能特征不同：

- reactive 是 Proxy，依赖收集精确到每个属性 key，触发更新也精确到 key 级别；
- ref 依赖收集是「整值」级别，所有对 .value 的依赖在同一个 key 下，触发粒度更粗；
- 对于大量独立基础类型状态，ref 开销略高（每个 ref 独立依赖表）；对于对象状态，reactive 更适合深度响应式追踪；
- Vue 3 的 compiler 优化（block tracking + hoisted props）可以缓解这个差异，实际项目通常差别可忽略。

```tsx
// RefImpl 的 get value()
get value() {
  trackRefValue(this)  // → track({}.__v_ref, 'get', 'value')
  return this._value
}

// 核心区别：
// 1. ref 只收集 {}.__v_ref 上 'value' 这个 key 的依赖
//    不管读的是 ref.value.count 还是 ref.value.name，
//    依赖收集的 key 永远是 'value'
// 2. reactive 精确到每个属性 key

// 因此：
const r = reactive({ count: 0, name: 'foo' })
// r.count 变化 → 只触发依赖了 count 的 effect
// r.name 变化 → 只触发依赖了 name 的 effect

const c = ref({ count: 0, name: 'foo' })
// c.value.count 变化 → 触发所有依赖 c.value 的 effect（粗粒度）
// c.value = { count: 1 } → 整个 c.value 的依赖全部触发
```

reactive 对象解构后，失去响应式连接。这是 reactive 最常踩的坑，ref 不存在这个问题。

```tsx
// ❌ reactive 解构 —— 失去响应式
const state = reactive({ count: 0 })
const { count } = state
// count 是普通 number，脱离了 Proxy 代理
count++              // ❌ 不生效！修改的是局部变量
state.count++        // ✅ 正确做法

// ✅ 用 toRefs 保持响应式
const { count } = toRefs(reactive({ count: 0 }))
count.value++        // ✅ 相当于 state.count++

// 源码证据：baseHandlers.ts get trap
get(target, key, receiver) {
  const res = Reflect.get(target, key, receiver)
  track(target, 'get', key)
  if (isRef(res)) return res  // ref 不递归，返回它本身
  if (isObject(res)) return reactive(res)
  return res
}
// 因此：reactive({ count: ref(0) }).count 仍是 ref，不需要 .value
```

```tsx
// reactive 数组：Proxy 自动劫持所有操作
const arr = reactive([1, 2, 3])
arr[0] = 10             // ✅ Proxy set trap 拦截
arr.push(4)            // ✅ 拦截（push 内部访问 length）
arr.filter(n => n > 1) // ✅ Proxy get trap 拦截

// ref 数组：必须通过 .value
const arrRef = ref([1, 2, 3])
arrRef.value[0] = 10    // ✅ 修改数组内容（_value 是 reactive 数组）
arrRef.value = [10,2,3] // ✅ 整体替换（triggerRefValue）
arrRef.value.push(4)    // ✅ push 返回新 length

// 陷阱：
// arrRef.value[0] = 99
// 修改了 reactive 数组的内容，通过 Proxy 拦截触发更新，
// 但 trigger 的是数组元素 '0' 上的依赖，
// 不是 ref 本身的 value 依赖表。
// 两种触发路径不同，效果一致但机制不同。
```

```tsx
// ref<T> 的类型推导
const count = ref(0)           // Ref<number>
const name = ref('foo')        // Ref<string>
const obj = ref({ a: 1 })     // Ref<{ a: number }>

// 读取时必须 .value —— TS 类型安全
count.value = 'hello'          // ❌ Type 'string' is not assignable

// reactive 的类型推导
const state = reactive({ count: 0 })
state.count = 'hello'          // ❌ TS 报错

// 但 reactive 有陷阱：
const arr = reactive([])       // never[]，类型丢失！
const arr = reactive<number[]>([])  // ✅ 必须手动指定泛型

// isRef 类型守卫
function isRef<T>(r: any): r is Ref<T>

// unref：自动去掉 .value
function unref<T>(ref: Ref<T> | T): T {
  return isRef(ref) ? ref.value : ref
}

// Ref 接口
interface Ref<T> { value: T }
```

```tsx
// reactive：变量本身是对象引用，可以直接替换
let state = reactive({ count: 0 })
state = reactive({ count: 1 })  // ✅ 直接替换引用

// 陷阱：函数内替换
function resetReactive() {
  state = reactive({ count: 0 })  // ❌ 改不了外部 state
}
// 必须通过代理：
function resetReactive() { state.count = 0 }

// ref：可以整体替换，也可以 .value 修改
let count = ref(0)
count.value = 1            // ✅ 修改内部值
count = ref(2)             // ✅ 替换整个 ref 对象

// ref 的函数参数替换：
function resetRef() { count.value = 0 }  // ✅ 写入 _value
function resetRef2() { count = ref(0) }   // ✅ 替换了外部变量
```

从实现看，两者性能特征不同：

- reactive 是 Proxy，依赖收集精确到每个属性 key，触发更新也精确到 key 级别；
- ref 依赖收集是「整值」级别，所有对 .value 的依赖在同一个 key 下，触发粒度更粗；
- 对于大量独立基础类型，ref 开销略高；对于对象状态，reactive 更适合深度追踪；
- Vue 3 的 compiler 优化（block tracking + hoisted props）缓解了这个差异。

## 八、实战选择指南

- **基本类型（number / string / boolean）→ 必须用 ref
reactive() 包装基本类型会报运行时警告：「value cannot be made reactive」**
- **对象 / 数组 → 优先 reactive，注意解构问题，用 toRefs 解构**
- **需要 track / untrack 或手动控制响应式 → ref（如自定义 composable 内部状态）**
- **template 中 ref 自动解包（<script setup>）→ 不需要 .value，更简洁**
- **reactive 对象中嵌套 ref → reactive 内部特殊处理，访问属性得到的 ref 不需要 .value**

## 九、关键源码文件索引

```tsx
packages/reactivity/src/
├── ref.ts
│   ├── createRef()           # 入口，isRef 判断
│   ├── RefImpl class        # get/set value(), trackRefValue(), triggerRefValue()
│   ├── convert()             # shallow vs deep 的值转换（isObject → reactive）
│   ├── isRef()               # 类型守卫
│   └── toRef() / toRefs()    # 解构工具
├── reactive.ts               # reactive(), __v_isReactive 标记防止重复代理
├── baseHandlers.ts
│   ├── reactiveHandler.get() # get trap（含 isRef 判断，深度响应式递归）
│   ├── reactiveHandler.set() # set trap（hasChanged 防止无意义触发）
│   ├── readonlyHandler       # 只读版本（不允许写操作）
│   └── shallowHandlers       # 浅层版本（不递归）
├── effect.ts
│   ├── TargetMap (WeakMap)   # 依赖表：target → key → Set<Dep>
│   └── ActiveEffect          # 当前执行的 effect
└── watch.ts                 # watchEffect 对 ref 和 reactive 的统一处理
                            # （自动识别 Ref/reactive，自动建立依赖）
```

## 十、常见问答

Q: reactive 能监听整个对象替换吗？
A: 不能。reactive() 接收的是对象引用，如果直接 state = { new: 'value' }，state 变成新的普通对象，失去了响应式连接。必须通过 state.key = 'value' 来修改。

Q: ref 的 .value 为什么要手动写？
A: 因为 JS 没有操作符重载，无法劫持 = 号。这也带来优势：所有修改都显式可见，代码更清晰。template 中 Vue compiler 会自动去掉 .value，用户感受不到差异。

Q: watch / watchEffect 对 ref 和 reactive 有区别吗？
A: 没有。Vue 3 内部会统一处理，自动建立依赖。watch(source, cb) 的 source 可以是 ref、reactive、Getter 函数，或它们的数组。