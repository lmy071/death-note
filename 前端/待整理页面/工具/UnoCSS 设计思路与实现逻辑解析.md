# UnoCSS 设计思路与实现逻辑解析

# UnoCSS 设计思路与实现逻辑解析

> 来源：[https://github.com/unocss/unocss](https://github.com/unocss/unocss)
> 

> 作者：Anthony Fu
> 

> 整理时间：2026-05-27
> 

---

## 一、项目背景与核心设计目标

### 1.1 传统 Atomic CSS 的痛点

传统 Atomic CSS（如 Tailwind CSS）存在以下核心问题：

1. **预设工具类固定**：Tailwind 内置了大量工具类，用户只能在其框架内使用，自定义设计系统困难
2. **生成大量无用 CSS**：即便使用 JIT（Just-In-Time）模式，仍存在解析、AST 扫描等开销
3. **插件系统复杂**：Tailwind 的插件系统耦合度高，难以做极致的性能优化
4. **体积难以控制**：功能越丰富，打包体积越大

### 1.2 UnoCSS 的设计目标

| 目标 | 实现方式 |
| --- | --- |
| **极致性能** | 无解析、无 AST、无扫描，比 Windi CSS / Tailwind JIT 快 5 倍 |
| **完全可定制** | 核心不内置任何工具类，所有功能通过 Preset 提供 |
| **极小体积** | ~6kb min+brotli，零依赖，浏览器友好 |
| **按需生成** | 只在类名被使用时才生成对应 CSS，真正的 on-demand |

---

## 二、核心设计思路

### 2.1 「引擎化」架构

UnoCSS 的最大设计创新：**将 Atomic CSS 工具抽象为一个通用引擎（Engine）**，而非一个固定的 CSS 框架。

```
┌─────────────────────────────────────────┐
│            @unocss/core  (引擎)         │
│                                         │
│  提取器 → 匹配器 → 生成器 → CSS 输出   │
│                                         │
│  核心不内置任何工具类                    │
└──────────────┬──────────────────────────┘
               │
       ┌───────┴────────┐
       │    Presets      │
       ├────────────────┤
       │ @unocss/preset-uno (默认)                      │
       │ @unocss/preset-mini           │
       │ @unocss/preset-wind3 (兼容 Tailwind)          │
       │ 自定义 Preset...              │
       └───────────────────────────────┘
```

**核心思想**：引擎只负责「提取 → 匹配 → 生成」的流水线，所有具体工具类的定义完全由 Preset 注入。这带来了极致的可扩展性。

### 2.2 On-Demand 生成哲学

传统方案：扫描源码 → 解析 AST → 提取类名 → 生成 CSS  

UnoCSS：直接从源码提取候选类名 → 与规则匹配 → 即时生成 CSS

**关键优化**：UnoCSS 不做完整的 AST 解析，而是通过简单的文本提取（split-based extractor）获取候选类名，再与动态规则进行正则匹配。这省去了昂贵的解析步骤，是性能提升 5x 的核心原因。

### 2.3 正则驱动的动态规则

这是 UnoCSS 最精巧的设计之一。规则不再是静态的键值对映射，而是 **「正则匹配器 + 动态处理函数」**：

```tsx
// 静态规则：一对一映射
rules: [
  ['m-1', { margin: '0.25rem' }],
]

// 动态规则：正则匹配 + 动态生成
rules: [
  [/^m-(\d+)$/, ([, d]) => ({ margin: `${d / 4}rem` })],
]
```

用户写 `m-100` → 正则 `/^m-(\d+)$/` 匹配 → 捕获组 `100` → 处理函数返回 `{ margin: '25rem' }` → 生成 `.m-100 { margin: 25rem }`

**设计优势**：

- 一条动态规则 = 无限个工具类（m-1 到 m-9999 全部覆盖）
- 支持任意参数，如 `m-7.5`、`p-3.2` 等
- 规则数量极少（几十个动态规则覆盖 Tailwind 上千个工具类）

---

## 三、实现逻辑解析

### 3.1 整体架构与数据流

```
源代码 (.html/.vue/.jsx/...)
        │
        ▼
┌─────────────────┐
│    Extractors    │ ← 从源代码中提取候选类名
│  (可自定义)      │
└────────┬────────┘
         │  候选类名列表: ['m-4', 'hover:bg-blue-500', ...]
         ▼
┌─────────────────┐
│    Variants      │ ← 处理变体（hover:, focus:, sm:, dark:, ...）
│  (前缀处理)      │    hover:m-4 → 提取 hover: → 传递给后续处理
└────────┬────────┘
         │  处理后的类名: 'm-4' + variantHandlers: [hoverHandler]
         ▼
┌─────────────────┐
│     Rules       │ ← 核心匹配：正则 matcher → 生成 CSS 对象
│  (规则匹配)      │
└────────┬────────┘
         │  CSS 对象: { margin: '1rem' }
         ▼
┌─────────────────┐
│   CSS 生成器     │ ← 将 CSS 对象转换为实际 CSS 字符串
│  (apply variants)│   应用 variant 的 selector 变换（如添加 :hover）
└────────┬────────┘
         │
         ▼
    最终 CSS 输出
```

### 3.2 提取器（Extractors）机制

**默认提取器**：`extractorSplit`

UnoCSS 的默认提取器极其简单——它通过空格、引号、括号等分隔符将源码拆分成 token，然后将这些 token 直接作为候选类名送给匹配引擎。

```tsx
// 默认 extractorSplit 简化逻辑
export function extractorSplit(code: string) {
  // 按空格、引号、括号、> 等分隔符拆分
  const tokens = code.split(/[\s"'>`{}]+/)
  return tokens.filter(t => t.length > 0)
}
```

**为什么这么简单却够用？**  

因为 UnoCSS 的规则匹配是正则驱动的，不需要提前知道类名是否「合法」——匹配不上就忽略，匹配上了就生成。这与 Tailwind 需要预先定义所有合法类名形成鲜明对比。

**自定义提取器**：用户可以实现自己的提取器来处理特殊场景（如 Pug 模板语法、Attributify 模式等）。

### 3.3 规则（Rules）系统详解

#### 静态规则

```tsx
rules: [
  ['m-1', { margin: '0.25rem' }],
  ['flex', { display: 'flex' }],
]
```

- matcher 是精确字符串，直接比较
- body 是静态 CSS 对象
- 性能最优，推荐在可以确定所有取值时使用

#### 动态规则

```tsx
rules: [
  // 基础动态规则
  [/^m-(\d+)$/, ([, d]) => ({ margin: `${d / 4}rem` })],
  
  // 带上下文的动态规则
  [/^p-(\d+)$/, (match, ctx) => ({
    padding: `${match[1] / 4}rem`
  })],
  
  // 返回多规则（CSS fallback）
  [/^h-(\d+)dvh$/, ([, d]) => [
    ['height', `${d}vh`],
    ['height', `${d}dvh`],  // 新旧语法 fallback
  ]],
]
```

**匹配流水线**：

1. 候选类名依次传递给每个 rule 的 matcher
2. matcher 是字符串 → 精确比较；matcher 是 RegExp → 正则测试
3. 匹配成功 → 调用 body 函数，传入 match 结果和上下文
4. 上下文包含：`theme`、`symbols`、`rawSelector`、`currentSelector`、`variantHandlers` 等

#### 特殊 Symbols 机制

UnoCSS v0.61+ 引入了 `symbols` 系统，允许规则动态控制生成的 CSS 结构：

```tsx
import { symbols } from '@unocss/core'

rules: [
  [/^grid$/, ([, d], { symbols }) => ({
    [symbols.parent]: '@supports (display: grid)',  // 外层 @supports 包裹
    display: 'grid',
  })],
]
// 生成：
// @supports (display: grid) {
//   .grid { display: grid; }
// }
```

可用 symbols：

| Symbol | 作用 |
| --- | --- |
| `symbols.parent` | 为生成的 CSS 规则添加父级包装（如 @supports, @media） |
| `symbols.selector` | 动态修改选择器（如添加 `:hover`、`:is()` 包装） |
| `symbols.layer` | 设置 CSS 层级 |
| `symbols.variants` | 当前规则应用的变体处理器数组 |
| `symbols.shortcutsNoMerge` | 禁止在 shortcuts 中合并 |
| `symbols.noMerge` | 禁止规则合并 |
| `symbols.sort` | 覆盖排序优先级 |
| `symbols.body` | 完全控制生成的 CSS 规则体 |

#### 多选择器规则（Generator 函数）

```tsx
rules: [
  [/^button-(.+)$/, function* ([, color], { symbols }) {
    yield { background: color }
    yield {
      [symbols.selector]: selector => `${selector}:hover`,
      background: `color-mix(in srgb, ${color} 90%, black)`,
    }
  }],
]
// 生成两条 CSS 规则：
// .button-red { background: red; }
// .button-red:hover { background: color-mix(in srgb, red 90%, black); }
```

### 3.4 变体（Variants）系统

变体是 UnoCSS 最强大的特性之一，它实现了「前缀修饰符」的效果（如 `hover:bg-red-500`、`sm:m-4`、`dark:text-white`）。

#### 变体匹配流水线

以 `hover:m-2` 为例：

```
输入: "hover:m-2"
    │
    ▼
变体匹配器 1: (matcher) => matcher.startsWith('hover:') ? {...} : null
    │ 匹配成功！
    │ 返回: { matcher: "m-2", selector: s => `${s}:hover` }
    │
    ▼
规则匹配器: /^m-(\d+)$/ 测试 "m-2"
    │ 匹配成功！
    │ 生成: { margin: '0.5rem' }
    │
    ▼
应用变体变换: selector => `${s}:hover`
    │
    ▼
最终 CSS: ".hover\\:m-2:hover { margin: 0.5rem; }"
```

#### 变体实现示例

```tsx
variants: [
  // hover: 变体
  (matcher) => {
    if (!matcher.startsWith('hover:'))
      return matcher  // 不匹配，原样返回
    
    return {
      // 去掉 hover: 前缀，交给后续匹配
      matcher: matcher.slice(6),
      // 变换最终 CSS 选择器
      selector: s => `${s}:hover`,
    }
  },
  
  // 响应式断点变体（如 sm:, md:, lg:）
  (matcher) => {
    const match = matcher.match(/^(\w+):(.+)/)
    if (!match) return matcher
    
    const [, breakpoint, rest] = match
    const bp = theme.breakpoints?.[breakpoint]
    if (!bp) return matcher
    
    return {
      matcher: rest,
      parent: `@media (min-width: ${bp})`,
    }
  },
]
```

**变体可以链式组合**：`hover:sm:dark:bg-red-500` → 依次经过三个变体处理 → 生成带 `:hover`、`@media (min-width: 640px)` 和 `.dark` 选择器的 CSS。

### 3.5 预设（Presets）系统

Preset 是 UnoCSS 的「插件单位」，一个 Preset 可以包含：

- `rules`：工具类规则
- `variants`：变体处理器
- `shortcuts`：快捷方式
- `theme`：主题变量
- `extractors`：自定义提取器
- `prefix`：类名前缀

```tsx
// 自定义 Preset 示例
import { definePreset, type Preset } from 'unocss'

export const myPreset: Preset = definePreset({
  name: 'my-design-system',
  
  rules: [
    [/^m-(\d+)$/, ([, d]) => ({ margin: `${d}px` })],
    [/^p-(\d+)$/, ([, d]) => ({ padding: `${d}px` })],
  ],
  
  variants: [
    // 自定义变体
    (matcher) => matcher.startsWith('active:') 
      ? { matcher: matcher.slice(7), selector: s => `.${s}.active` }
      : matcher
  ],
  
  shortcuts: {
    'btn': 'py-2 px-4 bg-blue-500 rounded',
  },
  
  theme: {
    colors: {
      primary: '#007bff',
    }
  }
})
```

**官方 Presets**：

| Preset | 说明 |
| --- | --- |
| `@unocss/preset-uno` | 默认预设，兼容 Windi CSS / Tailwind 常用工具类 |
| `@unocss/preset-mini` | 最小化预设，仅包含最基础工具类 |
| `@unocss/preset-wind3` | 完全兼容 Tailwind CSS v3 的预设 |
| `@unocss/preset-attributify` | Attributify 模式（`<div text="sm gray-500">`） |
| `@unocss/preset-icons` | 纯 CSS 图标支持 |
| `@unocss/preset-tagify` | 将 HTML 标签映射为工具类 |
| `@unocss/preset-web-fonts` | 网页字体按需加载 |

### 3.6 快捷方式（Shortcuts）系统

Shortcuts 将多个工具类合并为一个别名，类似 Windi CSS 的 shortcuts。

```tsx
shortcuts: {
  // 静态快捷方式
  'btn': 'py-2 px-4 font-semibold rounded-lg shadow-md',
  'btn-green': 'text-white bg-green-500 hover:bg-green-700',
  
  // 动态快捷方式
  /^btn-(.*)$/: ([, c]) => `bg-${c}-400 text-${c}-100 py-2 px-4 rounded-lg`,
}
```

**动态 Shortcuts 的强大之处**：一条定义生成无限快捷方式  

`btn-green` → 应用 green-400 背景 + green-100 文字  

`btn-red` → 应用 red-400 背景 + red-100 文字

### 3.7 CSS 生成与优化

#### 规则合并（Rules Merging）

UnoCSS 默认会将 body 相同的 CSS 规则合并，最小化输出体积：

```html
<!-- 输入 -->
<div class="m-2 hover:m-2">
```

```css
/* 默认输出（合并后） */
.hover\:m-2:hover,
.m-2 { margin: 0.5rem; }
```

相比不合并（两条独立规则），节省了重复声明。

可通过 `symbols.noMerge` 或规则级别配置禁用合并。

#### 排序（Ordering）

UnoCSS 尊重规则在配置中的定义顺序，后定义的规则优先级更高。  

动态规则匹配多个 token 时，同一规则内的匹配结果按字母序排序。

---

## 四、核心技术创新点

### 4.1 无解析架构

| 方案 | 处理方式 | 性能 |
| --- | --- | --- |
| Tailwind JIT | 扫描源码 → 解析 AST → 提取类名 → 生成 | 较慢 |
| Windi CSS | 扫描源码 → 解析 AST → 提取类名 → 生成 | 较慢 |
| **UnoCSS** | **拆分 token → 正则匹配 → 生成** | **极快（5x）** |

UnoCSS 完全跳过了 AST 解析步骤，通过简单的 split 提取 + 正则匹配完成整个流水线。

### 4.2 完全运行时（CDN Runtime）

由于核心引擎零依赖、~6kb 的超小体积，UnoCSS 可以直接通过 CDN 在浏览器运行时使用：

```html
<script src="https://cdn.jsdelivr.net/npm/unocss/runtime"></script>
<script>
  // 在浏览器中动态生成 CSS
  UnoCSS.generate('m-4 p-2 text-red-500')
</script>
```

这是传统 Atomic CSS 框架无法做到的。

### 4.3 Attributify 模式

UnoCSS 首创（后成标准）的 Attributify 模式，将类名搬到属性中，大幅减少类名字符串长度：

```html
<!-- 传统模式：类名很长 -->
<div class="text-sm text-gray-500 hover:text-gray-700 font-medium">
  
<!-- Attributify 模式：属性分组 -->
<div text="sm gray-500 hover:gray-700" font="medium">
```

### 4.4 纯 CSS 图标

通过 `@unocss/preset-icons`，可以将任意图标当作一个 CSS 类使用，图标以 Data URI 内联，无额外网络请求：

```html
<div class="i-carbon-home"> <!-- 首页图标 -->
<div class="i-mdi-account"> <!-- 用户图标 -->
```

---

## 五、与 Tailwind CSS / Windi CSS 的对比

| 维度 | Tailwind CSS | Windi CSS | **UnoCSS** |
| --- | --- | --- | --- |
| 架构 | PostCSS 插件 | 独立编译器 | **独立引擎（可嵌入任何环境）** |
| 核心工具类 | 内置（固定） | 内置 | **无（全部通过 Preset 提供）** |
| 按需生成 | JIT 模式（v3） | 原生支持 | **原生支持（设计目标）** |
| 解析方式 | AST 扫描 | AST 扫描 | **无解析（split + 正则）** |
| 性能 | 基准 | ~1x | **~5x** |
| 体积 | ~3MB（全量） | ~1MB | **~6kb（核心引擎）** |
| 可扩展性 | 插件系统 | 有限 | **极致（引擎化架构）** |
| 运行时使用 | 不支持 | 不支持 | **支持（CDN Runtime）** |
| 浏览器友好 | 否 | 否 | **是** |

---

## 六、总结

UnoCSS 的本质是一次对 Atomic CSS 范式的**重新想象（Reimagine）**：

1. **架构上**：从「框架」变成「引擎」，通过 Preset 系统实现真正的模块化
2. **性能上**：通过放弃 AST 解析，用正则匹配实现数量级的性能提升
3. **体积上**：核心引擎零内置规则，~6kb 做到了传统框架无法企及的轻量
4. **体验上**：动态规则 + 变体系统 + Attributify 模式，让写法更灵活
5. **创新上**：纯 CSS 图标、CDN 运行时、Inspector 调试工具等特性打开了 Atomic CSS 的新想象空间

> 💡 **推荐阅读**：作者 Anthony Fu 的原博客文章 [Reimagine Atomic CSS](https://antfu.me/posts/reimagine-atomic-css) 详细阐述了 UnoCSS 的设计心路历程。
>