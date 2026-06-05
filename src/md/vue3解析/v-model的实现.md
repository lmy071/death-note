# v-model 的实现原理

## 一、v-model 是什么

`v-model` 是 Vue 中用于实现**双向数据绑定**的指令，它本质上是**语法糖**——在底层将绑定拆解为一个属性绑定和一个事件监听器的组合。

```html
<!-- 使用 v-model -->
<input v-model="msg" />

<!-- 等价于 -->
<input :value="msg" @input="msg = $event.target.value" />
```

---

## 二、编译阶段：模板 → 渲染函数

Vue 3 的编译器会将 `v-model` 指令转换为对应的属性绑定和事件绑定。编译产物可在 [Vue Template Explorer](https://template-explorer.vuejs.org/) 中查看。

### 2.1 原生 input 元素

**模板：**
```html
<input v-model="msg" />
```

**编译输出：**
```js
_hoist_1 = /*#__PURE__*/ _withId((e) => (msg.value = e.target.value))

return _createElementVNode("input", {
  onChange: _hoist_1,
  modelValue: msg.value,
  onInput: _hoist_1
}, null, 40 /* PROPS, NEED_PATCH */, ["modelValue", "onInput"])
```

核心变换：
- `v-model="msg"` → `:modelValue="msg"` + `@update:modelValue="msg = $event"`
- 对于原生 `<input>`，Vue 运行时会进一步将 `modelValue` 映射到 `value`，将 `update:modelValue` 映射到 `input`/`change` 事件

### 2.2 组件上的 v-model

**模板：**
```html
<ChildComp v-model="msg" />
```

**编译输出：**
```js
_createVNode(ChildComp, {
  modelValue: msg.value,
  "onUpdate:modelValue": $event => (msg.value = $event)
})
```

组件上的 v-model 直接编译为：
- `:modelValue="msg"` — 向子组件传递值
- `@update:modelValue="msg = $event"` — 监听子组件触发的事件

### 2.3 带参数的 v-model

Vue 3 支持带参数的 v-model，如 `v-model:title="msg"`：

**模板：**
```html
<ChildComp v-model:title="msg" />
```

**编译输出：**
```js
_createVNode(ChildComp, {
  title: msg.value,
  "onUpdate:title": $event => (msg.value = $event)
})
```

参数名替换了默认的 `modelValue`，事件名变为 `update:title`。

---

## 三、运行时：vModelDirective

编译阶段只负责将 `v-model` 转为属性和事件，真正处理原生表单元素适配的是 Vue 运行时的 **vModel 指令**。

源码位置：`packages/runtime-dom/src/directives/vModel.ts`

### 3.1 指令注册

```js
export const vModelText: Directive = {
  created(el, { modifiers: { lazy, trim, number } }, vnode) {
    // 根据修饰符决定事件类型
    el._assign = getModelAssigner(vnode)
    el.addEventListener(lazy ? "change" : "input", (e) => {
      // ... 处理 trim / number 修饰符
    })
  },
  mounted(el, { value }) {
    el.value = value  // 初始值设置
  },
  beforeUpdate(el, { value, modifiers: { lazy, trim, number } }, vnode) {
    el._assign = getModelAssigner(vnode)
    // 避免光标跳动：如果值没变，不更新
    if (document.activeElement !== el) {
      el.value = value
    }
  }
}
```

### 3.2 不同表单元素的处理

Vue 为不同类型的表单元素注册了不同的指令：

| 元素 | 指令 | 绑定属性 | 监听事件 |
|------|------|----------|----------|
| `<input type="text">` | vModelText | value | input / change |
| `<textarea>` | vModelText | value | input / change |
| `<input type="checkbox">` | vModelCheckbox | checked | change |
| `<input type="radio">` | vModelRadio | checked | change |
| `<select>` | vModelSelect | value (多选时为 []) | change |

### 3.3 修饰符处理

```js
// lazy：将 input 事件改为 change 事件
el.addEventListener(lazy ? "change" : "input", handler)

// number：自动将值转为 Number
if (number || el.type === "number") {
  val = looseToNumber(val)
}

// trim：自动去除首尾空格
if (trim) {
  val = val.trim()
}
```

| 修饰符 | 作用 | 实现方式 |
|--------|------|----------|
| `.lazy` | 改为在 `change` 事件时更新（而非 `input`） | 替换监听事件类型 |
| `.number` | 自动将输入值转为数字 | `looseToNumber()` 转换 |
| `.trim` | 自动去除首尾空格 | `String.trim()` 处理 |

---

## 四、自定义组件的 v-model

### 4.1 Vue 3 默认约定

Vue 3 中组件 v-model 的默认 prop 名为 `modelValue`，事件名为 `update:modelValue`：

```vue
<!-- 子组件 -->
<template>
  <input
    :value="modelValue"
    @input="$emit('update:modelValue', $event.target.value)"
  />
</template>

<script setup>
defineProps(['modelValue'])
defineEmits(['update:modelValue'])
</script>
```

### 4.2 自定义 v-model 参数名

```vue
<!-- 父组件 -->
<ChildComp v-model:title="pageTitle" />

<!-- 子组件 -->
<script setup>
defineProps(['title'])
defineEmits(['update:title'])
</script>
```

### 4.3 多个 v-model 绑定

Vue 3 支持在同一个组件上使用多个 v-model：

```vue
<!-- 父组件 -->
<UserForm v-model:first-name="first" v-model:last-name="last" />

<!-- 子组件 -->
<script setup>
defineProps(['firstName', 'lastName'])
defineEmits(['update:firstName', 'update:lastName'])
</script>
```

### 4.4 自定义 v-model 修饰符

```vue
<!-- 父组件 -->
<ChildComp v-model.capitalize="msg" />

<!-- 子组件 -->
<script setup>
const props = defineProps(['modelValue', 'modelModifiers'])
const emit = defineEmits(['update:modelValue'])

function handleInput(e) {
  let value = e.target.value
  // modelModifiers 对象包含传入的修饰符
  if (props.modelModifiers.capitalize) {
    value = value.charAt(0).toUpperCase() + value.slice(1)
  }
  emit('update:modelValue', value)
}
</script>
```

---

## 五、响应式系统：数据变化如何触发视图更新

v-model 的"双向"离不开 Vue 的响应式系统：

```
用户输入 → DOM 事件触发 → 修改响应式数据 → 依赖收集触发 → 重新渲染 → DOM 更新
```

### 5.1 ref 的依赖追踪

```js
import { ref } from 'vue'

const msg = ref('hello')
// 内部：msg = { __v_isRef: true, _value: 'hello', dep: <Dep> }

// 读取 msg.value 时 → track(dep, TrackOpTypes.GET, 'value')
// 设置 msg.value 时 → trigger(dep, TriggerOpTypes.SET, 'value')
```

### 5.2 完整数据流

```
                    ┌─────────────────────────────────────┐
                    │           Vue 响应式系统              │
                    │                                     │
  用户输入           │  ref/reactive                       │
  ────────→         │  ┌──────┐    track     ┌──────────┐ │
  DOM Event         │  │ msg  │ ──────────→  │ effect   │ │
                    │  │ ref  │              │ (render) │ │
                    │  └──┬───┘    trigger   └────┬─────┘ │
                    │     │ ─────────────────→     │       │
                    │     │                        ↓       │
                    │     │                   重新渲染      │
                    └─────│────────────────────────────────┘
                          │
                          ↓
                    更新 DOM (value/checked)
```

1. **用户输入** → 触发 `input`/`change` 事件
2. **事件处理器** → 修改 `ref.value`
3. **trigger** → 通知所有依赖此 ref 的 effect
4. **渲染 effect** → 重新执行组件渲染函数
5. **patch** → 对比新旧 VNode，更新 DOM

---

## 六、Vue 2 vs Vue 3 的 v-model 差异

| 特性 | Vue 2 | Vue 3 |
|------|-------|-------|
| 默认 prop 名 | `value` | `modelValue` |
| 默认事件名 | `input` | `update:modelValue` |
| 自定义 prop/事件 | `model: { prop, event }` | `v-model:arg` 参数语法 |
| 多个 v-model | ❌ 不支持 | ✅ 支持 |
| 修饰符自定义 | 仅内置修饰符 | ✅ 组件可自定义修饰符 |
| `.sync` 修饰符 | ✅ 支持 | ❌ 移除（被 v-model:arg 替代） |
| `.native` 修饰符 | ✅ 支持 | ❌ 移除 |

### Vue 2 的 v-model

```vue
<!-- 父组件 -->
<ChildComp v-model="msg" />

<!-- 子组件 -->
<script>
export default {
  props: ['value'],
  methods: {
    handleInput(e) {
      this.$emit('input', e.target.value)
    }
  }
}
</script>
```

### Vue 3 的 v-model（同功能）

```vue
<!-- 父组件 -->
<ChildComp v-model="msg" />

<!-- 子组件 -->
<script setup>
defineProps(['modelValue'])
defineEmits(['update:modelValue'])
</script>
```

---

## 七、完整源码追踪

以 `<input v-model="msg" />` 为例，从模板到 DOM 更新的完整链路：

### Step 1: 编译

```
模板: <input v-model="msg" />
        ↓ compiler-sfc / compiler-dom
渲染函数:
_createElementVNode("input", {
  modelValue: msg.value,
  onInput: e => (msg.value = e.target.value)
})
```

### Step 2: 挂载

```
渲染函数执行
        ↓
创建 input VNode，带 vModelText 指令
        ↓
patch → mountElement → 创建 DOM <input>
        ↓
invokeDirectiveHook → vModelText.created
  → 设置 el.value = msg.value
  → 绑定 input 事件监听器
        ↓
invokeDirectiveHook → vModelText.mounted
  → 确保值已同步
```

### Step 3: 用户输入

```
用户在 input 中键入 "H"
        ↓
触发 input 事件
        ↓
vModelText 的事件处理器:
  const value = el.value  // "H"
  el._assign(value)       // msg.value = "H"
        ↓
ref trigger → 渲染 effect 被调度
        ↓
组件重新渲染，生成新 VNode
        ↓
patch 旧 VNode vs 新 VNode
        ↓
vModelText.beforeUpdate
  → 如果当前元素不是焦点，更新 el.value
  → 如果是焦点，跳过（避免光标重置）
```

### Step 4: 光标保护

Vue 3 在 `beforeUpdate` 中做了一个关键优化——如果 input 正在被用户编辑（`document.activeElement === el`），则**不会更新 `el.value`**，避免光标位置被重置：

```js
beforeUpdate(el, { value }, vnode) {
  if (document.activeElement !== el) {
    el.value = value
  }
}
```

---

## 八、最佳实践

### 8.1 组件设计

```vue
<!-- ✅ 推荐：使用 defineModel (Vue 3.4+) -->
<script setup>
const model = defineModel()
</script>

<template>
  <input v-model="model" />
</template>
```

```vue
<!-- ✅ 兼容写法：props + emit -->
<script setup>
const props = defineProps(['modelValue'])
const emit = defineEmits(['update:modelValue'])
</script>

<template>
  <input :value="props.modelValue" @input="emit('update:modelValue', $event.target.value)" />
</template>
```

### 8.2 避免直接修改 prop

```vue
<!-- ❌ 错误：直接修改 prop -->
<script setup>
const props = defineProps(['modelValue'])
// 不能直接 props.modelValue = newValue
</script>

<!-- ✅ 正确：通过 emit 通知父组件 -->
<script setup>
const emit = defineEmits(['update:modelValue'])
emit('update:modelValue', newValue)
</script>
```

### 8.3 复杂表单的 v-model

```vue
<script setup>
import { ref, watch } from 'vue'

const formData = ref({
  name: '',
  email: '',
  age: 0
})

// 深层监听，可用于表单校验等
watch(() => formData.value, (val) => {
  console.log('表单变化:', val)
}, { deep: true })
</script>

<template>
  <input v-model="formData.name" />
  <input v-model="formData.email" />
  <input v-model.number="formData.age" />
</template>
```

---

## 九、总结

```
v-model = :modelValue + @update:modelValue （语法糖）
```

| 层级 | 作用 |
|------|------|
| **编译器** | 将 `v-model` 指令展开为属性绑定 + 事件绑定 |
| **运行时指令** | 处理原生表单元素的差异化适配（value/checked/事件类型） |
| **响应式系统** | 驱动数据变化 → 视图更新的自动刷新 |
| **组件通信** | 通过 props + emit 实现父子组件间的双向数据流 |

核心要点：
1. v-model 本质是**单向数据流 + 事件通知**的组合，并非真正的"双向绑定"
2. 数据流向始终是：**父 → 子（props）**，子 → 父（emit 事件）
3. 响应式系统负责数据变化后的视图自动更新
4. Vue 3 相比 Vue 2 的改进：支持多 v-model、自定义修饰符、参数化绑定
5. `defineModel()`（Vue 3.4+）进一步简化了组件 v-model 的写法
