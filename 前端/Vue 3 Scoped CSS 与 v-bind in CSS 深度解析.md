# Vue 3 Scoped CSS 与 v-bind in CSS 深度解析

# Vue 3 Scoped CSS 与 v-bind in CSS 深度解析

<aside>
💬 基于 `vuejs/core` 仓库（v3.5.35）源码分析。

</aside>

<aside>
💬 涵盖：Scoped CSS 选择器重写 → v-bind() CSS 变量注入 → 运行时 DOM 属性挂载

</aside>

---

# 一、架构全景

```
┌──────────────────────────────────────────────────────────────────────┐
│                        编译时（compiler-sfc）                          │
│                                                                      │
│  parse.ts ──→ 解析 SFC，提取 <style> 块 + cssVars + slotted 标志     │
│     │                                                                │
│     ├── compileStyle.ts ──→ PostCSS 插件链处理每个 <style> 块         │
│     │     ├── cssVarsPlugin    : v-bind(expr) → var(--hash)          │
│     │     ├── trimPlugin       : 空白规范化                          │
│     │     ├── scopedPlugin     : 选择器 → [data-v-xxx]               │
│     │     └── postcssModules   : CSS Modules 类名映射（可选）          │
│     │                                                                │
│     ├── compileScript.ts ──→ STEP 7: 注入 useCssVars() 调用          │
│     │                        生成 CSS 变量 → 组件实例的映射           │
│     │                                                                │
│     └── compileTemplate.ts ──→ 传递 scopeId + ssrCssVars 给编译器     │
│                                                                      │
├──────────────────────────────────────────────────────────────────────┤
│                        运行时（runtime-dom）                          │
│                                                                      │
│  renderer.ts ──→ 元素挂载时调用 nodeOps.setScopeId(el, scopeId)      │
│     │            el.setAttribute('data-v-xxxxx', '')                 │
│     │                                                                │
│  useCssVars.ts ──→ 组件挂载后：                                      │
│     │              getter(proxy) → 计算 CSS 变量值                   │
│     │              setVarsOnVNode → 遍历 VNode 树                     │
│     │              style.setProperty(--hash, value)                  │
│     │              MutationObserver 监听父节点 DOM 变化               │
```

```
│     │              onBeforeUpdate → queuePostFlushCb(setVars)        │
│     │                                                                │
│  modules/style.ts ──→ patchStyle 处理 v-bind:style + v-show 优先级   │
│                       合并 CSS_VAR_TEXT 到 style.cssText             │
└──────────────────────────────────────────────────────────────────────┘
```

---

# 二、Scoped CSS：选择器重写

## 2.1 核心原理

Vue 的 Scoped CSS 通过 PostCSS 插件 `pluginScoped` 实现，为每个 CSS 选择器添加唯一的 `[data-v-xxxxx]` 属性选择器作为作用域限定。

### 编译时

组件编译后，所有 `<style scoped>` 中的选择器被改写：

```css
/* 源码 */
.example { color: red; }

/* 编译后 */
.example[data-v-f3f3eg9] { color: red; }
```

### 运行时

组件渲染时，`renderer.ts` 在 `mountElement` 阶段调用 `nodeOps.setScopeId`：

```tsx
// renderer.ts L695-696
// scopeId
setScopeId(el, vnode, vnode.scopeId, slotScopeIds, parentComponent)
```

```tsx
// nodeOps.ts L126-128
setScopeId(el, id) {
  el.setAttribute(id, '')  // el.setAttribute('data-v-f3f3eg9', '')
}
```

**组件模板根元素**自动获得 `data-v-xxxxx` 属性。由于 CSS 选择器已写为 `.example[data-v-xxxxx]`，只有带该属性的元素才会匹配，实现了组件作用域隔离。

## 2.2 选择器重写规则

| 原始 CSS | 编译后 | 说明 | |----------|--------|------| | `.foo` | `.foo[data-v-xxx]` | 普通选择器 — 属性后置 | | `.foo .bar` | `.foo .bar[data-v-xxx]` | 只给**最后一个**选择器加属性 | | `*` | `[data-v-xxx]` | 通配符直接替换 | | `* .foo` | `[data-v-xxx] .foo` | 省略 `*` 并前置属性 | | `div > span` | `div > span[data-v-xxx]` | combinator 不影响插入位置 | | `.foo, .bar` | `.foo[data-v-xxx], .bar[data-v-xxx]` | 每个选择器独立处理 |

### 流程图

```
输入：.parent .child { color: red; }
    │
    ▼
selectorParser 解析为 AST
    │
    ├── .parent (class node)
    ├── [space combinator]
    └── .child  (class node)  ← 最后一个节点，插入点
    │
    ▼
.insertAfter(.child, attribute('[data-v-xxx]'))
    │
    ▼
输出：.parent .child[data-v-xxx] { color: red; }
```

## 2.3 Deep 选择器

`:deep()` 穿透当前组件的 Scoped 隔离，让它里面的选择器匹配子组件内部元素。

```
原始                  编译后
────────────────────────────────────────
:deep(.bar)         → [data-v-xxx] .bar
.foo :deep(.bar)    → .foo[data-v-xxx] .bar
```

### 实现细节

```tsx
// pluginScoped.ts — rewriteSelector 中的 deep 处理
if (value === ':deep' || value === '::v-deep') {
  ;(rule as any).__deep = true          // 标记整个规则为 deep
  if (n.nodes.length) {
    // .foo :deep(.bar) → 展开内部节点、插入空格 combinator、删除伪元素
    let last = n
    n.nodes[0].each(ss => {
      selector.insertAfter(last, ss)
      last = ss
    })
    selector.removeChild(n)             // 移除 :deep() 包装
  }
  return false
}
```

关键逻辑：

1. `(rule as any).__deep = true` — 标记此规则不需要注入 scoped 属性
2. 展开 `:deep()` 内层选择器到外层，替换伪元素节点
3. 在 `:deep()` 前插入空格 combinator（如果前一个节点不是空格）

## 2.4 Slotted 选择器

`:slotted()` 限定 slot 内容的样式作用域，使用独立的 `-s` 后缀属性。

```
原始                      编译后
───────────────────────────────────────────────
:slotted(.slot)         → [data-v-xxx-s] .slot
```

```tsx
// pluginScoped.ts
if (value === ':slotted' || value === '::v-slotted') {
  rewriteSelector(id, rule, n.nodes[0], selectorRoot, deep, true /* slotted */)
  // 展开内部节点...
  shouldInject = false  // slotted 属性已限定作用域，不再加普通 scoped 属性
  return false
}
```

区别于普通 Scoped：

- 属性名：`data-v-xxxxx-s` 而非 `data-v-xxxxx`
- 属性**前置**于选择器（`[data-v-xxx-s] .slot`），因为 slot 内容来自父组件，属性在父组件模板中
- 不需要额外的 `[data-v-xxx]` 属性（`shouldInject = false`）

## 2.5 Global 选择器

`:global()` 完全跳过 Scoped 处理，保留原始选择器。

```
原始                      编译后
───────────────────────────────────────────────
:global(.baz)           → .baz
```

```tsx
// pluginScoped.ts
if (value === ':global' || value === '::v-global') {
  selector.replaceWith(n.nodes[0])  // 直接用内部选择器替换
  return false
}
```

## 2.6 Deep 容器伪类处理

当 `:is()` / `:where()` / `:has()` / `:not()` 中混合了普通选择器和 `:deep()` 时，是 Scoped CSS 最复杂的场景。

### 场景 1：:not 内的 deep — 前置属性

```css
/* 原始 */
.parent :not(.a, :deep(.b)) .child

/* 编译后 */
.parent[data-v-xxx] :not(.a, [data-v-xxx] .b) .child
```

`:not` 不可拆分，只能在当前选择器之前插入 scoped 属性。

### 场景 2：:is/:where/:has 内的 deep — 拆分规则

```css
/* 原始 */
.parent :is(.a, :deep(.b)) .child

/* 编译后（拆为两条规则） */
.parent .a[data-v-xxx] .child,
.parent[data-v-xxx] .b .child
```

```tsx
// splitSelectorForNestedDeep — 拆分核心
function splitSelectorForNestedDeep(id, rule, selector, selectorRoot, pseudo, deep, slotted) {
  const pseudoIndex = selector.index(pseudo)
  const selectors = pseudo.nodes.map((branch, index) => {
    const branchSelector = selector.clone()      // 克隆整个选择器
    const branchPseudo = branchSelector.at(pseudoIndex)  // 定位伪元素位置
    branchPseudo.removeAll()
    branchPseudo.append(branch.clone())          // 只保留一个分支
    rewriteSelector(id, rule, branchSelector, ...) // 递归重写每个分支
    return branchSelector
  })
  selector.replaceWith(...selectors)              // 替换为多个独立选择器
}
```

### 场景 3：纯 deep 容器 — 递归处理

```css
/* 原始 */
.parent :is(:deep(.a), :deep(.b)) .child

/* 编译后 */
.parent[data-v-xxx] .a .child,
.parent[data-v-xxx] .b .child
```

当所有分支都是 `:deep()`（无混合）时，递归处理每个分支，不拆分规则。

## 2.7 关键帧（Keyframes）冲突避免

Scoped 下 `@keyframes` 也有唯一性需求：

```css
/* 原始 */
@keyframes fade { from { opacity: 0 } }
.foo { animation: fade 1s; }

/* 编译后 */
@keyframes fade-f3f3eg9 { from { opacity: 0 } }
.foo[data-v-f3f3eg9] { animation: fade-f3f3eg9 1s; }
```

```tsx
// pluginScoped.ts
AtRule(node) {
  if (keyframesRE.test(node.name) && !node.params.endsWith(`-${shortId}`)) {
    keyframes[node.params] = node.params = node.params + '-' + shortId
  }
},
OnceExit(root) {
  // 遍历所有 declaration，重写 animation/animation-name 中的引用
  root.walkDecls(decl => {
    if (animationNameRE.test(decl.prop)) {
      decl.value = decl.value.split(',').map(v => keyframes[v.trim()] || v.trim()).join(',')
    }
    if (animationRE.test(decl.prop)) {
      // 处理 animation 简写 → 查找 keyframes 名称位置并替换
    }
  })
}
```

## 2.8 规则前后缀分离（extractAndWrapNodes）

当一条 CSS 规则同时包含 declarations 和嵌套 rules 时，需要分离：

```css
/* 原始 */
.foo { color: red; .bar { font-size: 14px } }

/* 分离为 */
.foo { .bar { font-size: 14px } }
.foo { & { color: red } }
```

### 原因

如果 `.foo` 被改写为 `.foo[data-v-xxx]`，那么 `&` 嵌套的 `.bar` 会展开为 `.foo[data-v-xxx] .bar` — 保持正确的作用域。但如果 declarations 和嵌套 rule 混合，PostCSS 的嵌套展开会出问题。

```tsx
function extractAndWrapNodes(parentNode) {
  const nodes = parentNode.nodes.filter(n => n.type === 'decl' || n.type === 'comment')
  if (nodes.length) {
    for (const node of nodes) parentNode.removeChild(node)
    const wrappedRule = new Rule({ nodes, selector: '&' })
    parentNode.prepend(wrappedRule)
  }
}
```

### 流程图

```
输入：.foo { color: red; .bar { ... }; margin: 0; }
    │
    ├── 提取 declarations → ['color: red', 'margin: 0']
    ├── 创建新 Rule → .foo { & { color: red; margin: 0 } }
    ├── prepend 到原规则
    │
    ▼
输出：
  .foo {
    & { color: red; margin: 0 }   ← 展开后: .foo[data-v-xxx] { color: red; margin: 0 }
    .bar { ... }                  ← 展开后: .foo[data-v-xxx] .bar { ... }
  }
```

---

# 三、v-bind in CSS：编译时

## 3.1 核心原理

`v-bind()` 在 CSS 中的语法允许将组件状态值注入到样式中：

```
<style scoped>
.title {
  color: v-bind(color);
  font-size: v-bind('size + "px"');
}
</style>
```

这在编译时分两步处理：

1. `cssVarsPlugin`（PostCSS）将 `v-bind(expr)` 替换为 `var(--hash)`
2. `compileScript` 生成运行时代码调用 `useCssVars()`，建立 `--hash` ↔ 响应式值的映射

## 3.2 全流程

```
┌──────────────────────────────────────────────────────────────────┐
│ STEP 1: parse.ts — parseCssVars()                                │
│   从所有 <style> 中用正则 + 词法分析器提取 v-bind() 中的变量名     │
│   结果：sfc.cssVars = ['color', 'size + "px"']                   │
└──────────────────────┬───────────────────────────────────────────┘
                       ↓
┌──────────────────────────────────────────────────────────────────┐
│ STEP 2: compileStyle.ts — cssVarsPlugin (PostCSS)                │
│   Declaration 钩子中匹配 v-bind()，替换为 var(--hash)             │
│                                                                  │
│   v-bind(color)       →  var(--f3f3eg9-color)    (dev)          │
│   v-bind(size+'px')   →  var(--v4g5fx1)          (prod: hash)   │
└──────────────────────┬───────────────────────────────────────────┘
                       ↓
┌──────────────────────────────────────────────────────────────────┐
│ STEP 3: compileScript.ts — genCssVarsCode()                      │
│   生成运行时代码，注入到 <script setup> 末尾：                     │
│                                                                  │
│   _useCssVars(_ctx => ({                                         │
│     "--f3f3eg9-color": (_ctx.color),                             │
│     "--v4g5fx1": (_ctx.size + "px")                              │
│   }))                                                             │
└──────────────────────┬───────────────────────────────────────────┘
                       ↓
┌──────────────────────────────────────────────────────────────────┐
│ STEP 4: useCssVars.ts (运行时) — 组件挂载后执行                   │
│                                                                  │
│   1. getter(instance.proxy) → { '--hash': 'red', ... }           │
│   2. setVarsOnVNode → 遍历 VNode 树                               │
│   3. style.setProperty('--hash', 'red')                          │
```

```
│   4. MutationObserver 监听父节点 DOM 变化 → 刷新子组件变量         │
│   5. onBeforeUpdate → queuePostFlushCb(setVars)                  │
└──────────────────────────────────────────────────────────────────┘
```

## 3.3 parseCssVars：从 SFC 提取 CSS 变量

```tsx
// cssVars.ts
const vBindRE = /v-bind\s*\(/g

export function parseCssVars(sfc: SFCDescriptor): string[] {
  const vars: string[] = []
  sfc.styles.forEach(style => {
    // 先移除注释（避免误匹配）
    const content = style.content.replace(/\/\*([\s\S]*?)\*\/|\/\/.*/g, '')
    while ((match = vBindRE.exec(content))) {
      const start = match.index + match[0].length
      const end = lexBinding(content, start)  // 词法分析器找 closing )
      if (end !== null) {
        const variable = normalizeExpression(content.slice(start, end))
        if (!vars.includes(variable)) vars.push(variable)
      }
    }
  })
  return vars
}
```

### lexBinding：嵌套括号词法分析器

```
输入：v-bind(fn(a, b))
            ↑ start=7

状态机遍历：
  i=7  '('  → parenDepth: 1
  i=8  'a'  → 普通字符
  i=9  ','  → 普通字符
  i=10 'b'  → 普通字符
  i=11 ')'  → parenDepth: 0 → return 11

结果：content.slice(7, 11) = "fn(a, b)"
```

词法分析器正确处理：

- **嵌套括号**：`v-bind(fn(a, g(x)))` → 匹配最外层 `)`
- **字符串字面量**：`v-bind('hello(world)')` → 忽略引号内的括号

## 3.4 cssVarsPlugin：PostCSS 替换

```tsx
// cssVars.ts
export const cssVarsPlugin: PluginCreator<CssVarsPluginOptions> = opts => {
  const { id, isProd } = opts
  return {
    postcssPlugin: 'vue-sfc-vars',
    Declaration(decl) {
      const value = decl.value
      if (vBindRE.test(value)) {
        vBindRE.lastIndex = 0
        let transformed = ''
        let lastIndex = 0
        let match
        while ((match = vBindRE.exec(value))) {
          const start = match.index + match[0].length
          const end = lexBinding(value, start)
          if (end !== null) {
            const variable = normalizeExpression(value.slice(start, end))
            transformed +=
              value.slice(lastIndex, match.index) +
              `var(--${genVarName(id, variable, isProd)})`  // ← 核心替换
            lastIndex = end + 1
          }
        }
        decl.value = transformed + value.slice(lastIndex)
      }
    },
  }
}
```

### genVarName：变量命名策略

| 环境 | 命名 | 示例 | 策略 | |------|------|------|------| | Dev | `{id}-{escapedName}` | `f3f3eg9-color` | 可读可调试 | | Prod | `hash(id + raw)` | `v4g5fx1` | 最小长度 |

```tsx
function genVarName(id: string, raw: string, isProd: boolean, isSSR = false): string {
  if (isProd) {
    // hash 首字符不能是数字（CSS 自定义属性命名规则 → 前缀 'v'）
    return hash(id + raw).replace(/^\d/, r => `v${r}`)
  } else {
    return `${id}-${getEscapedCssVarName(raw, isSSR)}`
  }
}
```

## 3.5 genCssVarsCode：生成运行时代码

```tsx
// cssVars.ts
export function genCssVarsCode(vars, bindings, id, isProd) {
  const varsExp = genCssVarsFromList(vars, id, isProd)
  // varsExp = `{\n  "--hash1": (expr1),\n  "--hash2": (expr2)\n}`

  // 使用 compiler-dom 的 processExpression 处理前缀标识符
  const exp = createSimpleExpression(varsExp, false)
  const context = createTransformContext(createRoot([]), {
    prefixIdentifiers: true,
    inline: true,
    bindingMetadata: bindings,
  })
  const transformed = processExpression(exp, context)

  return `_${CSS_VARS_HELPER}(_ctx => (${transformedString}))`
  // 最终输出类似：
  // _useCssVars(_ctx => ({ "--hash": (_ctx.color), ... }))
}
```

## 3.6 compileScript 中的注入

```tsx
// compileScript.ts — STEP 7
if (sfc.cssVars.length && !options.templateOptions?.ssr) {
  ctx.helperImports.add(CSS_VARS_HELPER)   // import { useCssVars } from 'vue'
  ctx.helperImports.add('unref')           // import { unref } from 'vue'
  ctx.s.prependLeft(startOffset,
    `\n${genCssVarsCode(sfc.cssVars, ctx.bindingMetadata, scopeId, !!options.isProd)}\n`
  )
}
```

生成的 `<script setup>` 末尾会多出类似这样的代码：

```jsx
import { useCssVars as _useCssVars, unref as _unref } from 'vue'

_useCssVars(_ctx => ({
  "--f3f3eg9-color": (unref(_ctx.color)),
  "--v4g5fx1": (unref(_ctx.size) + "px")
}))
```

### Options API 支持

```tsx
// genNormalScriptCssVarsCode
// 用于 <script>（非 setup）场景：
// 1. import { useCssVars } from 'vue'
// 2. 包装原 setup() 函数，前后注入 __injectCSSVars__()
export function genNormalScriptCssVarsCode(cssVars, bindings, id, isProd, defaultVar) {
  return (
    `\nimport { ${CSS_VARS_HELPER} as _${CSS_VARS_HELPER} } from 'vue'\n` +
    `const __injectCSSVars__ = () => {\n${genCssVarsCode(cssVars, bindings, id, isProd)}\n` +
    `const __setup__ = ${defaultVar}.setup\n` +
    `${defaultVar}.setup = __setup__\n` +
    `  ? (props, ctx) => { __injectCSSVars__(); return __setup__(props, ctx) }\n` +
    `  : __injectCSSVars__\n`
  )
}
```

---

# 四、useCssVars：运行时

## 4.1 核心工作流

```
组件挂载
    │
    ├── onMounted
    │   ├── watch(setVars, NOOP, { flush: 'post' })
    │   │   └── 依赖变化 → flush: 'post' → DOM 更新后再写 CSS 变量
    │   │
    │   ├── new MutationObserver(setVars)
    │   │   └── 监听父节点 DOM 变化（子组件根节点影响）
    │   │
    │   └── onUnmounted → ob.disconnect()
    │
    ├── onBeforeUpdate
    │   └── queuePostFlushCb(setVars)  // 延迟到 flush 后避免同步阻塞
    │
    └── setVars() 核心
        ├── getter(instance.proxy) → { '--hash': value, ... }
        ├── setVarsOnVNode(instance.subTree, vars)
        │   ├── 组件 → 递归 subtree
        │   ├── ELEMENT → setVarsOnNode(el, vars)
        │   │   └── style.setProperty('--hash', value) × N
        │   │   └── (style)[CSS_VAR_TEXT] = '--hash: value; ...'
        │   ├── Fragment → 遍历 children
        │   └── Static → while(el !== anchor) 遍历静态节点
        └── updateTeleports(vars)  // 更新 Teleport 目标的 CSS 变量
```

## 4.2 完整源代码

```tsx
// useCssVars.ts
export function useCssVars(getter: (ctx: any) => Record<string, unknown>): void {
  if (!__BROWSER__ && !__TEST__) return

  const instance = getCurrentInstance()

  // Teleport 批量更新
  const updateTeleports = (instance.ut = (vars = getter(instance.proxy)) => {
    Array.from(
      document.querySelectorAll(`[data-v-owner="${instance.uid}"]`),
    ).forEach(node => setVarsOnNode(node, vars))
  })

  const setVars = () => {
    const vars = getter(instance.proxy)
    if (instance.ce) {
      setVarsOnNode(instance.ce as any, vars)          // Custom Element
    } else {
      setVarsOnVNode(instance.subTree, vars)            // 普通组件
    }
    updateTeleports(vars)                               // Teleport 目标
  }

  onBeforeUpdate(() => { queuePostFlushCb(setVars) })   // 延迟到 flush 后

  onMounted(() => {
    watch(setVars, NOOP, { flush: 'post' })             // 响应式追踪
    const ob = new MutationObserver(setVars)             // DOM 结构变化
    ob.observe(instance.subTree.el!.parentNode, { childList: true })
    onUnmounted(() => ob.disconnect())
  })
}
```

## 4.3 CSS_VAR_TEXT 和 patchStyle 集成

`useCssVars` 在设置 CSS 变量时，同时缓存 CSS 文本：

```tsx
// setVarsOnNode
function setVarsOnNode(el: Node, vars: Record<string, unknown>) {
  if (el.nodeType === 1) {
    const style = (el as HTMLElement).style
    let cssText = ''
    for (const key in vars) {
      const value = normalizeCssVarValue(vars[key])
      style.setProperty(`--${key}`, value)
      cssText += `--${key}: ${value};`
    }
    ;(style as any)[CSS_VAR_TEXT] = cssText   // ← 缓存
  }
}
```

当 `patchStyle` 通过 `style.cssText = '...'` 覆盖整个 style 时，CSS 变量会丢失。因此：

```tsx
// modules/style.ts
if (isCssString) {
  if (prev !== next) {
    const cssVarText = (style as any)[CSS_VAR_TEXT]
    if (cssVarText) {
      ;(next as string) += ';' + cssVarText    // ← 合并 CSS 变量到 cssText
    }
    style.cssText = next as string
  }
}
```

---

# 五、v-bind in CSS 的响应式链路

```
<template>
  <div class="box">hello</div>
</template>

<script setup>
import { ref } from 'vue'
const color = ref('red')
</script>

<style scoped>
.box {
  color: v-bind(color);
}
</style>
```

### 编译输出

**<style> → CSS：**

```css
.box[data-v-f3f3eg9] {
  color: var(--f3f3eg9-color);
}
```

**<script setup> 末尾注入：**

```jsx
import { useCssVars as _useCssVars, unref as _unref } from 'vue'

_useCssVars(_ctx => ({
  "--f3f3eg9-color": (_unref(_ctx.color))
}))
```

### 运行时响应链路

```
color.value = 'blue'
    │
    ├── Proxy set trap → trigger
    │
    ├── 组件重新渲染（template 可能没有引用 color → 无 VNode 更新）
    │   但 useCssVars 内部 watch(setVars, NOOP, { flush: 'post' })
    │   已追踪 getter 中的 _ctx.color 读取
    │
    ├── watch 的 scheduler 被触发
    │   └── flush: 'post' → 在 DOM 更新后执行 setVars()
    │
    ├── setVars()
    │   ├── getter(instance.proxy) → { '--f3f3eg9-color': 'blue' }
    │   └── setVarsOnVNode(subTree, vars)
    │       └── style.setProperty('--f3f3eg9-color', 'blue')
    │
    └── 浏览器重新计算样式 → .box 文字变蓝
```

**关键点：**

1. **template 无需引用变量**— `watch(setVars, NOOP)` 在 `setVars()` 执行时重新读取 `getter(proxy)`，自动追踪 CSS 变量中引用的所有响应式值
2. **模板不变但有副作用**— `onBeforeUpdate → queuePostFlushCb(setVars)` 确保即使组件因其他原因重渲染，CSS 变量也会同步
3. **MutationObserver 保底**— 如果父节点的子节点列表变化（如子组件根元素被替换），CSS 变量会被重新写入

---

# 六、性能设计

| 机制 | 策略 | 为什么 | |------|------|--------| | `queuePostFlushCb` | onBeforeUpdate 不直接 setVars，加入 post-flush 队列 | 避免同步阻塞 render 管线 | | `watch({ flush: 'post' })` | DOM 更新后再写 CSS 变量 | 确保读取到的 DOM 是最新状态 | | `MutationObserver` | 仅监听 `childList` | 只在 DOM 结构变化时刷新，不监听属性 | | `CSS_VAR_TEXT` 缓存 | 字符串拼接后直接赋值 `style.cssText` | 避免 patchStyle 覆盖 CSS 变量时逐一重建 | | `prefixCache` | 自动前缀查询结果缓存 | Webkit/Moz/ms 前缀检测只需一次 | | `WeakSet<processedRules>` | 跳过已处理的 PostCSS Rule | 避免递归重复处理 |

## 6.1 编译时优化：Shadow DOM 模式

当 Web Component 使用 Shadow DOM 时，Scoped CSS 不需要 `[data-v-xxx]` 属性选择器（Shadow DOM 天然隔离），编译时通过 `__FEATURE_PROD_DEVTOOLS__` 常量在 production build 中跳过不必要代码。

## 6.2 SSR 特殊处理

SSR 模式下 CSS 变量名称前加 `:` 前缀：

```tsx
genVarName: isSSR ? `--:${hash}` : `--${hash}`
genCssVarsFromList: `":--${genVarName(...)}'`
```

`ssrRenderStyle` 在序列化 HTML 时识别 `:` 前缀 → 输出 `style="--hash: value"`。同时需要在客户端 hydration 时重置为 `initial` 避免继承外部同属性值。

---

# 七、文档总结

## 关键文件依赖关系

```
parse.ts (SFC 解析)
    │
    ├── cssVars.ts (v-bind in CSS)
    │   ├── parseCssVars()           ← parse.ts 调用提取变量
    │   ├── cssVarsPlugin            ← compileStyle.ts 使用
    │   ├── genCssVarsCode()         ← compileScript.ts 使用
    │   └── genNormalScriptCssVarsCode() ← Options API 使用
    │
    ├── compileStyle.ts (样式编译入口)
    │   ├── cssVarsPlugin            ← v-bind → var(--hash)
    │   ├── pluginTrim.ts            ← 空白规范化
    │   ├── pluginScoped.ts          ← 选择器 → [data-v-xxx]
    │   └── postcss-modules          ← CSS Modules (异步)
    │
    ├── compileScript.ts
    │   └── STEP 7: genCssVarsCode   ← 注入 useCssVars() 调用
    │
    └── compileTemplate.ts
        ├── scopeId: longId          ← 传给编译器
        └── ssrCssVars               ← SSR CSS 变量映射

runtime-dom/src/
    ├── helpers/useCssVars.ts        ← 运行时 CSS 变量设置
    ├── modules/style.ts             ← patchStyle + CSS_VAR_TEXT 合并
    └── nodeOps.ts                   ← setScopeId → el.setAttribute
```

## 核心洞察

1. **Scoped 是纯编译时方案**— PostCSS 重写选择器 + 运行时在根元素上 `setAttribute`，不需要 Shadow DOM，兼容性极好
2. **v-bind in CSS 是编译时+运行时协作**— 编译时提取变量并替换为 `var(--hash)`，运行时通过 `watch` 建立响应式映射
3. **`CSS_VAR_TEXT` 是防御性设计**— 防止 `style.cssText` 全量覆盖时丢失 CSS 变量，用 Symbol key 存储在 style 对象上
4. **scoped 属性只加在模板根元素上**— 但选择器重写为 `.foo[data-v-xxx]` 而非 `[data-v-xxx] .foo`，意味着 CSS 属性选择器本身就是对当前组件 DOM 树的"向下限定"
5. **`:deep()` 的工作原理不是"移除属性选择器"**— 而是属性**前置**（`[data-v-xxx] .bar`），使得选择器的"起始点"从组件根开始，从而能匹配子组件内部的 `.bar` 元素

---