# Vue3 对比 Vue2 提升详解

# Vue3 对比 Vue2 提升详解

> Vue3 不是 Vue2 的小修小补，而是一次**从底层重写**的全面升级。以下从 12 个维度详细对比两者的差异和提升。
> 

---

## 一、响应式系统：Proxy 取代 Object.defineProperty

### 1.1 核心差异

| 对比维度 | Vue2 | Vue3 |
| --- | --- | --- |
| 底层机制 | `Object.defineProperty` | `Proxy`  • `Reflect` |
| 对象新增属性 | 无法检测 → 需要 `Vue.set()` | ✅ 天然支持 |
| 对象删除属性 | 无法检测 → 需要 `Vue.delete()` | ✅ 天然支持 |
| 数组索引修改 | ❌ `arr[0] = x` 不触发更新 | ✅ 天然支持 |
| 数组长度修改 | ❌ `arr.length = 0` 不触发更新 | ✅ 天然支持 |
| Map / Set / WeakMap / WeakSet | ❌ 不支持 | ✅ 原生支持 |
| 初始化性能 | 递归遍历所有属性转 getter/setter | 惰性响应式，访问时才转换 |

### 1.2 源码级差异

**Vue2 的局限性：**

```jsx
// Vue2 无法检测的操作
const vm = new Vue({
  data: { obj: {}, arr: [1, 2, 3] }
})

// ❌ 新增属性不触发更新
vm.obj.newProp = 'hello'          // 需要 Vue.set(vm.obj, 'newProp', 'hello')

// ❌ 删除属性不触发更新
delete vm.obj.existingProp        // 需要 Vue.delete(vm.obj, 'existingProp')

// ❌ 数组索引赋值不触发更新
vm.arr[0] = 100                   // 需要 Vue.set(vm.arr, 0, 100) 或 vm.arr.splice(0, 1, 100)

// ❌ 数组 length 不触发更新
vm.arr.length = 0                 // 需要 vm.arr = []
```

**Vue3 的天然支持：**

```jsx
// Vue3 — 全部天然支持
const state = reactive({ obj: {}, arr: [1, 2, 3] })

state.obj.newProp = 'hello'       // ✅ 触发更新
delete state.obj.existingProp     // ✅ 触发更新
state.arr[0] = 100                // ✅ 触发更新
state.arr.length = 0              // ✅ 触发更新
```

### 1.3 Map / Set 支持

```jsx
// Vue3 新增的响应式集合支持
import { reactive } from 'vue'

const state = reactive({
  map: new Map([
    ['key1', 'value1']
  ]),
  set: new Set([1, 2, 3])
})

// 以下操作全部触发响应式更新
state.map.set('key2', 'value2')    // ✅ Map.set()
state.map.delete('key1')           // ✅ Map.delete()
state.map.clear()                  // ✅ Map.clear()
state.set.add(4)                   // ✅ Set.add()
state.set.delete(1)                // ✅ Set.delete()
```

> 💡 这是一项**质变**。Vue2 的数组重写方案需要 hack 7 个变异方法（push/pop/shift/unshift/splice/sort/reverse），Vue3 用 Proxy 彻底解决了这个问题。
> 

---

## 二、组合式 API（Composition API）vs 选项式 API（Options API）

### 2.1 对比示例

**Vue2 Options API：逻辑分散**

```jsx
export default {
  data() {
    return {
      count: 0,
      searchText: '',
      searchResult: [],
    }
  },
  watch: {
    searchText: {
      handler: 'fetchData',
      immediate: true,
    }
  },
  methods: {
    increment() { this.count++ },
    async fetchData() {
      this.searchResult = await api.search(this.searchText)
    }
  }
}
// 问题：count 相关逻辑散落在 data/methods 中
//       search 相关逻辑散落在 data/watch/methods 中
```

**Vue3 Composition API：逻辑内聚**

```jsx
import { ref, watch } from 'vue'

// 计数逻辑 —— 完整封装在一个函数中
function useCounter() {
  const count = ref(0)
  const increment = () => count.value++
  return { count, increment }
}

// 搜索逻辑 —— 完整封装在一个函数中
function useSearch() {
  const searchText = ref('')
  const searchResult = ref([])
  watch(searchText, async () => {
    searchResult.value = await api.search(searchText.value)
  }, { immediate: true })
  return { searchText, searchResult }
}

// 组件中使用
setup() {
  const { count, increment } = useCounter()
  const { searchText, searchResult } = useSearch()
  return { count, increment, searchText, searchResult }
}
```

### 2.2 setup 语法糖（`<script setup>`）

```
<script setup>
import { ref, watch } from 'vue'

// 更简洁：不需要 return，顶层绑定自动暴露给模板
const count = ref(0)
const increment = () => count.value++

watch(count, (val) => {
  console.log(`count changed to: ${val}`)
})
</script>

<template>
  <button @click="increment">{{ count }}</button>
</template>
```

### 2.3 核心优势表

| 优势 | 说明 |
| --- | --- |
| **逻辑复用** | 组合函数（composables）——不再是 mixin 的混入冲突地狱 |
| **逻辑内聚** | 同一功能的 data/watch/methods 写在一起，而非按选项分类 |
| **类型推导** | `ref` / `reactive` 返回的类型 IDE 自动推导 |
| **Tree-shaking** | 按需引入，未使用的 API 不会打包 |
| **代码组织** | 大组件不再有"滚屏找代码"的痛苦 |

> 💡 Vue3 **保留了 Options API**，Vue2 用户无需重写代码就能迁移。
> 

---

## 三、虚拟 DOM 重写 + 编译时优化

这是 Vue3 性能提升的**最大来源**。

### 3.1 静态提升（Static Hoisting）

**Vue2 的渲染函数：**

```jsx
// 每次 re-render 都重新创建 VNode
render() {
  return createVNode('div', null, [
    createVNode('span', null, 'Hello World'),  // 静态文本也每次重建
  ])
}
```

**Vue3 的编译结果：**

```jsx
// 静态节点提升到 render 函数外，只创建一次
const _hoisted_1 = createVNode('span', null, 'Hello World')

render() {
  return createVNode('div', null, [_hoisted_1])  // 直接复用
}
```

### 3.2 PatchFlag（动态标记）

```html
<!-- 模板 -->
<div>
  <span>静态文本</span>
  <span>{{ dynamicText }}</span>
  <span :id="dynamicId">静态文本</span>
</div>
```

```jsx
// Vue3 编译结果（简化版）
import { createVNode as _createVNode, toDisplayString as _toDisplayString } from 'vue'

const _hoisted_1 = _createVNode('span', null, '静态文本')

export function render() {
  return _createVNode('div', null, [
    _hoisted_1,
    _createVNode('span', null, _toDisplayString(dynamicText), 1 /* TEXT */),
    _createVNode('span', { id: dynamicId }, '静态文本', 8 /* PROPS */, ['id'])
  ])
}
```

**PatchFlag 不止标记，还指导 diff 算法跳过不需要的比对：**

| PatchFlag | 值 | 含义 |
| --- | --- | --- |
| TEXT | 1 | 动态文本内容 |
| CLASS | 2 | 动态 class |
| STYLE | 4 | 动态 style |
| PROPS | 8 | 动态属性（非 class/style） |
| FULL_PROPS | 16 | 动态 key |
| HYDRATE_EVENTS | 32 | 带事件的 Fragment |
| STABLE_FRAGMENT | 64 | 子节点顺序稳定的 Fragment |
| KEYED_FRAGMENT | 128 | 带 key 的 Fragment |
| NEED_PATCH | 512 | 非优化模式 |

### 3.3 Block Tree（块树）

```
Vue2 Diff（全量递归）：
  Root
  ├─ div           ← 对比
  │  ├─ span       ← 对比（即使它是静态的）
  │  ├─ span       ← 对比
  │  └─ span       ← 对比
  └─ div           ← 对比
     └─ p          ← 对比

Vue3 Block Tree（跳过静态）：
  编译时：把模板划分为「块」
  ┌─ Block 根节点
  │  ├─ [动态子节点] span (TEXT patchFlag)
  │  └─ [动态子节点] span (PROPS patchFlag)
  └─ 静态节点全部跳过！
```

> 🚀 结果：Vue3 的 diff 只需要比对比 Vue2 **少得多的节点数**，尤其是静态内容多的页面。
> 

---

## 四、性能量化对比

| 指标 | Vue2 | Vue3 | 提升 |
| --- | --- | --- | --- |
| 包体积（gzip） | ~23KB | ~13KB | **-43%** |
| 初始渲染 | 基准 | **最快 55% 提升** | 1.5-2x |
| 更新 | 基准 | **最快 133% 提升** | 2-2.3x |
| 内存占用 | 基准 | **减少 54%** | ~2x |
| 服务端渲染 | 基准 | **最快 2-3x** | 2-3x |

---

## 五、Tree-shaking 支持

### 5.1 Vue2 的问题

```jsx
// Vue2：无论用不用，new Vue 时全局 API 全部引入
import Vue from 'vue'
Vue.nextTick(() => {})
Vue.set(obj, 'key', val)     // 即使你不用
Vue.delete(obj, 'key')       // 这些也全在包里
Vue.observable(obj)
```

### 5.2 Vue3 的按需引入

```jsx
// Vue3：只用你引入的
import { ref, computed, watch, nextTick } from 'vue'
// 未使用的 API 在打包时被 tree-shake 掉
```

### 5.3 可 tree-shake 的模块

```
Vue3 全局 API 全部改为具名导出：
  ✓ nextTick     ✓ ref       ✓ reactive     ✓ computed
  ✓ watch        ✓ watchEffect              ✓ toRefs
  ✓ v-model 指令                            ✓ v-show 指令
  ✓ <Transition> ✓ <KeepAlive>             ✓ <Teleport>

结果：只用 10 个 API → 打包体积比 Vue2 小 40%+
```

---

## 六、TypeScript 支持

| 维度 | Vue2 | Vue3 |
| --- | --- | --- |
| 源码语言 | Flow（已过时） | TypeScript |
| 类型推导 | Class API（装饰器）需要额外插件 | `ref<T>()` 自动推导类型 |
| 组件 Props 类型 | 运行时 `props: { x: Number }` | 支持纯类型声明 `defineProps<{ x: number }>()` |
| IDE 支持 | 一般 | 优秀（Volar 插件） |
| 响应式变量在模板中 | 无类型提示 | ✅ 自动推导 |

### 6.1 props 纯类型声明

```
<script setup lang="ts">
// Vue3：用 TypeScript 类型声明 props
interface Props {
  title: string
  count?: number
  items: string[]
}

const props = defineProps<Props>()
// props.title 自动推导为 string
</script>
```

对比 Vue2：

```jsx
// Vue2：只能用运行时验证
props: {
  title: { type: String, required: true },
  count: { type: Number, default: 0 },
}
```

---

## 七、组件架构升级

### 7.1 Fragments（多根节点）

```
<!-- Vue2：必须有唯一根节点 -->
<template>
  <div>  <!-- 多余的包裹层 -->
    <p>Hello</p>
    <p>World</p>
  </div>
</template>

<!-- Vue3：可直接写多个根节点 -->
<template>
  <p>Hello</p>
  <p>World</p>
</template>
```

> 🎉 减少了大量无意义的 `<div>` 包裹，DOM 结构更干净。
> 

### 7.2 Teleport（传送门）

```
<!-- 将内容渲染到指定 DOM 节点 -->
<template>
  <button @click="showModal = true">打开弹窗</button>

  <Teleport to="body">
    <div v-if="showModal" class="modal">
      我是 body 下的弹窗，不受父组件 overflow:hidden 的影响
    </div>
  </Teleport>
</template>
```

> 🎯 解决弹窗、下拉菜单等被父元素 `overflow: hidden` 裁剪的问题。
> 

### 7.3 Suspense（异步组件协调）

```
<template>
  <Suspense>
    <!-- 异步组件加载中显示 fallback -->
    <template #default>
      <AsyncDashboard />
    </template>
    <template #fallback>
      <LoadingSpinner />
    </template>
  </Suspense>
</template>
```

---

## 八、生命周期变化

| Vue2 | Vue3（Options API） | Vue3（Composition API） |
| --- | --- | --- |
| `beforeCreate` | `beforeCreate` | `setup()` 本身（更早） |
| `created` | `created` | `setup()` 本身 |
| `beforeMount` | `beforeMount` | `onBeforeMount` |
| `mounted` | `mounted` | `onMounted` |
| `beforeUpdate` | `beforeUpdate` | `onBeforeUpdate` |
| `updated` | `updated` | `onUpdated` |
| `beforeDestroy` | `beforeUnmount` | `onBeforeUnmount` |
| `destroyed` | `unmounted` | `onUnmounted` |
| `errorCaptured` | `errorCaptured` | `onErrorCaptured` |
| — | `renderTracked` 🆕 | `onRenderTracked` 🆕 |
| — | `renderTriggered` 🆕 | `onRenderTriggered` 🆕 |

**关键变化**：`destroyed` → `unmounted`（命名更语义化），新增调试用的 `renderTracked` / `renderTriggered`。

---

## 九、v-model 升级

### 9.1 统一语法

**Vue2：一个组件只能有一个 v-model**

```
<!-- value + input 事件是硬编码的 -->
<Child v-model="val" />

<!-- Vue2 中多 v-model 需要用 .sync -->
<Child :title.sync="title" :content.sync="content" />
```

**Vue3：多 v-model 原生支持**

```
<!-- 一个组件可以绑定多个 v-model -->
<UserForm
  v-model:name="name"
  v-model:email="email"
  v-model:age="age"
/>
```

```
<!-- 子组件内部 -->
<script setup>
const props = defineProps(['name', 'email', 'age'])
const emit = defineEmits(['update:name', 'update:email', 'update:age'])
</script>
```

### 9.2 自定义修饰符

```
<!-- 父组件 -->
<Child v-model.capitalize="text" />
```

```
<!-- 子组件 -->
<script setup>
const props = defineProps({
  modelValue: String,
  modelModifiers: { default: () => ({}) }
})

const emit = defineEmits(['update:modelValue'])

function updateValue(value) {
  if (props.modelModifiers.capitalize) {
    value = value.charAt(0).toUpperCase() + value.slice(1)
  }
  emit('update:modelValue', value)
}
</script>
```

---

## 十、`<script setup>` 编译器宏

| 宏 | 用途 |
| --- | --- |
| `defineProps` | 声明 props，支持 TS 类型 |
| `defineEmits` | 声明 emit 事件 |
| `defineExpose` | 暴露给父组件通过 ref 访问的内容 |
| `defineOptions` | 声明组件选项（name、inheritAttrs 等） |
| `defineModel` 🆕 | 简化 v-model（3.4+） |
| `defineSlots` 🆕 | 类型化 slot |

```
<script setup>
// 一行搞定 v-model（3.4+）
const modelValue = defineModel()

// props + emits 类型声明
const props = defineProps<{ title: string }>()
const emit = defineEmits<{ update: [value: string] }>()

// 暴露给父组件
defineExpose({ reset: () => { /* ... */ } })
</script>
```

---

## 十一、新内置组件与 API

| 新增项 | 作用 |
| --- | --- |
| `<Teleport>` | 传送门，将内容渲染到指定 DOM |
| `<Suspense>` | 异步组件协调，显示 fallback |
| `defineAsyncComponent` | 异步组件加载（替代 Vue2 的工厂函数方式） |
| `createRenderer` | 自定义渲染器（支持 Canvas、WebGL 等） |
| `effectScope` | 管理副作用作用域 |
| `shallowRef` | 浅响应式 ref（只追踪 .value） |
| `triggerRef` | 手动触发 shallowRef 更新 |
| `customRef` | 自定义 ref，完全控制追踪/触发逻辑 |
| `readonly` | 创建只读响应式代理 |
| `shallowReactive` | 浅响应式 reactive |
| `toRaw` | 获取响应式对象的原始对象 |
| `markRaw` | 标记对象永不转为响应式 |
| `isRef / unref / toRef / toRefs` | ref 工具函数集 |
| `watchEffect` | 自动追踪依赖的 watch |
| `watchPostEffect` | post flush 的 watchEffect |
| `watchSyncEffect` | 同步执行的 watchEffect |

---

## 十二、编译器与构建工具升级

| 维度 | Vue2 | Vue3 |
| --- | --- | --- |
| 编译器架构 | 运行时编译 | **编译时 + 运行时**，编译时做更多优化 |
| 构建工具 | vue-cli (Webpack) | **Vite**（ESM + esbuild + Rollup） |
| 开发服务器启动 | 10-30 秒 | **< 1 秒** |
| HMR 速度 | 随项目规模线性增长 | **几乎恒定**（仅重新编译变更模块） |
| 生产构建 | Webpack | Rollup（更快、输出更小） |
| 编译时优化 | 无 | 静态提升、PatchFlag、Block Tree、事件缓存 |
| JSX 支持 | ✅ | ✅ 原生支持 |

---

## 十三、Vue2 → Vue3 迁移对照表

| Vue2 写法 | Vue3 写法 |
| --- | --- |
| `Vue.set(obj, key, val)` | `obj.key = val` ✅ 原生支持 |
| `Vue.delete(obj, key)` | `delete obj.key` ✅ 原生支持 |
| `new Vue({ ... })` | `createApp({ ... }).mount('#app')` |
| `Vue.component('name', comp)` | `app.component('name', comp)` |
| `Vue.directive('name', dir)` | `app.directive('name', dir)` |
| `Vue.mixin({ ... })` | `app.mixin({ ... })` |
| `Vue.use(plugin)` | `app.use(plugin)` |
| `Vue.prototype.$http = axios` | `app.config.globalProperties.$http = axios` |
| `Vue.config.errorHandler` | `app.config.errorHandler` |
| `Vue.filter('name', fn)` | ❌ 已移除，用 computed 或方法替代 |
| `v-bind.sync="prop"` | `v-model:prop` |
| `v-bind="$attrs"` (透传) | ✅ 同 Vue2，但 `$attrs` 包含事件 |
| `$listeners` | ❌ 已移除，事件也在 `$attrs` 中 |
| `this.$on / $off / $once` | ❌ 已移除（事件总线），用 mitt 等替代 |
| `$children` | ❌ 已移除，用 `ref`  • `defineExpose` |
| `<template slot="header">` | `<template v-slot:header>` 或 `<template #header>` |
| `computed: { fn() {} }` | `computed(() => ...)` Composition API |
| `filters: { format(v) {} }` | ❌ 已移除，用函数代替 |

---

## 十四、Vue3 还能做的事（Vue2 做不到）

```
✅ 监听 Map / Set / WeakMap / WeakSet 的变化
✅ 监听数组索引赋值和 length 变化
✅ 监听对象属性的新增和删除
✅ 自定义渲染器（Canvas、终端、Three.js 等）
✅ 同时等待多个异步组件（Suspense + async setup）
✅ 真正的逻辑复用组合函数（无 mixin 冲突）
✅ 完整的 TypeScript 类型推导（包括模板中）
✅ 按需引入，未用到的 API 不进入打包
✅ 在 <script setup> 中直接使用顶层 await
✅ SSR + hydration 性能提升 2-3x
✅ 多根节点组件
✅ Teleport 传送门
✅ 1 秒启动的开发服务器（Vite）
```

---

## 十五、总结

```
┌─────────────────────────────────────────────────────────┐
│              Vue2 → Vue3 升级的核心逻辑                  │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  Vue2 的问题               →    Vue3 的答案              │
│                                                         │
│  Object.defineProperty     →    Proxy 完整拦截           │
│  逻辑分散的 Options API    →    逻辑内聚的 Composition   │
│  全量 Diff 虚拟 DOM        →    编译时优化 + Block Tree  │
│  无法 Tree-shake           →    按需引入，体积 -43%      │
│  Flow 类型                 →    原生 TypeScript          │
│  单根节点组件              →    Fragments 多根节点       │
│  vue-cli 慢速 HMR          →    Vite 秒级热更新          │
│  无法做自定义渲染器         →    createRenderer() API    │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

> 🚀 **一句话总结**：Vue3 用 Proxy 重写了响应式系统，用 Composition API 重新组织了代码逻辑，用编译时优化重写了虚拟 DOM，用 TypeScript 重写了整个代码库。它是同一个框架的影子——但内核已经完全不一样了。
> 

---

*参考资料：*

- Vue3 官方文档：[https://vuejs.org/](https://vuejs.org/)
- Vue3 迁移指南：[https://v3-migration.vuejs.org/](https://v3-migration.vuejs.org/)
- Vue3 源码：[https://github.com/vuejs/core](https://github.com/vuejs/core)