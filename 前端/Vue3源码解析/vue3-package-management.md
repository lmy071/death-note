# vue3-package-management

# Vue 3 包管理体系深度解析

> 基于 `vuejs/core` 仓库（v3.5.35，pnpm monorepo）分析。
> 
> 
> 涵盖：包管理器选型 → workspace 架构 → 依赖策略 → 14 个包详解 → 构建系统 → 发布流程
> 

---

# 一、包管理器

## 1.1 选型：pnpm

```
packageManager: pnpm@11.3.0
lockfileVersion: '9.0'
Node.js: >= 20.0.0
```

### 为什么是 pnpm？

| 特性 | pnpm | npm | yarn |
| --- | --- | --- | --- |
| 磁盘效率 | 全局 store + 硬链接，节省数 GB | 每项目独立 node_modules | 类似 npm |
| 安装速度 | 极快（并行 + 缓存） | 较慢 | 快 |
| 幽灵依赖 | **严格隔离**（只有声明过的才能访问） | 允许幽灵依赖 | 允许幽灵依赖 |
| workspace 协议 | `workspace:*` 原生支持 | `workspace:*` 支持 | `workspace:` 支持 |
| Catalog 协议 | ✅ pnpm v9+ 新特性 | ❌ | ❌ |
| lockfile | `pnpm-lock.yaml`，内容寻址 | `package-lock.json` | `yarn.lock` |

Vue 3 选择 pnpm 的三个关键原因：

1. **幽灵依赖隔离** — monorepo 中包之间只有显式声明的依赖才能 `import`，防止意外的跨包引用
2. **workspace 协议** — `"@vue/shared": "workspace:*"` 在开发时指向本地源码，发布时自动替换为版本号
3. **Catalog 协议** — Vue 3 是 pnpm catalog 的早期 adoptor，统一管理共享外部依赖版本

---

# 二、Workspace 架构

## 2.1 两层级结构

```
vue3/                               ← root（private）
├── packages/                        ← 公共发布包（14 个）
│   ├── compiler-core/               @vue/compiler-core
│   ├── compiler-dom/                @vue/compiler-dom
│   ├── compiler-sfc/                @vue/compiler-sfc
│   ├── compiler-ssr/                @vue/compiler-ssr
│   ├── reactivity/                  @vue/reactivity
│   ├── runtime-core/                @vue/runtime-core
│   ├── runtime-dom/                 @vue/runtime-dom
│   ├── runtime-test/                @vue/runtime-test（private）
│   ├── server-renderer/             @vue/server-renderer
│   ├── shared/                      @vue/shared
│   ├── vue/                         vue（主入口）
│   └── vue-compat/                  @vue/compat（Vue 2 兼容迁移）
│
└── packages-private/                ← 私有工具包（不发布到 npm）
    ├── dts-test/                    类型测试
    ├── dts-built-test/              构建品类型测试
    ├── sfc-playground/              SFC 在线 playground
    ├── template-explorer/           模板编译可视化
    └── vite-debug/                  Vite 调试辅助
```

## 2.2 pnpm-workspace.yaml

```yaml
packages:
-'packages/*'
-'packages-private/*'

# Catalog：统一管理共享外部依赖的版本
catalog:
'@babel/parser': ^7.29.3
'@babel/types': ^7.29.0
'entities':'^7.0.1'
'estree-walker': ^2.0.2
'magic-string': ^0.30.21
'source-map-js': ^1.2.1
'vite': ^8.0.14
'@vitejs/plugin-vue': ^6.0.7

# 允许在 npm postinstall 期间构建原生模块的包
allowBuilds:
'@swc/core':true
'esbuild':true
'puppeteer':true
'simple-git-hooks':true
'unrs-resolver':true

dedupePeers:true        # 去重 peer 依赖
minimumReleaseAge:1440  # 使用至少发布 1 天的包版本（稳定性）
```

### Catalog 协议详解

pnpm v9 引入的 catalog 允许在根 `pnpm-workspace.yaml` 统一声明共享依赖版本，各子包只需引用 `catalog:` 即可：

```json
// compiler-core/package.json
{
  "dependencies": {
    "@babel/parser": "catalog:",     // 自动解析为 ^7.29.3
    "entities": "catalog:",          // 自动解析为 ^7.0.1
    "estree-walker": "catalog:",     // 自动解析为 ^2.0.2
    "source-map-js": "catalog:",     // 自动解析为 ^1.2.1
    "@vue/shared": "workspace:*"      // workspace 内互引用
  }
}
```

**优势：**
- 单个文件统一升级版本，不用逐包修改
- 避免 monorepo 内同一外部依赖出现多个版本
- 发布时 `workspace:*` 自动替换为实际版本号

---

# 三、依赖策略

## 3.1 三种引用方式

| 协议 | 写法 | 用途 | 发布时 |
| --- | --- | --- | --- |
| `workspace:*` | `"@vue/shared": "workspace:*"` | monorepo 内部包互引用 | 替换为当前版本号（如 `3.5.35`） |
| `catalog:` | `"@babel/parser": "catalog:"` | 共享外部依赖 | 替换为 catalog 中声明的实际版本 |
| 直接版本号 | `"csstype": "^3.2.3"` | 独立外部依赖 | 保持原样 |

## 3.2 各包依赖矩阵

```
┌─────────────────────────────────────────────────────────────────┐
│                        外部依赖                                  │
│  @babel/parser  entities  estree-walker  magic-string           │
│  source-map-js  postcss  csstype                                 │
└──────────────────────┬──────────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────────┐
│                     @vue/shared                                  │
│                     (零依赖，基础工具层)                            │
└────┬──────────┬──────────┬──────────┬──────────┬────────────────┘
     │          │          │          │          │
     ▼          ▼          ▼          ▼          ▼
┌─────────┐ ┌────────┐ ┌────────┐ ┌────────┐ ┌────────────────┐
│reactivity│ │compiler│ │runtime │ │compiler│ │server-renderer │
│         │ │ -core  │ │ -core  │ │ -ssr   │ │                │
└────┬────┘ └───┬────┘ └───┬────┘ └───┬────┘ └───────┬────────┘
     │          │          │          │               │
     │          ▼          │          │               │
     │    ┌─────────┐      │          │               │
     │    │compiler │      │          │               │
     │    │ -dom    │      │          │               │
     │    └────┬────┘      │          │               │
     │         │           │          │               │
     ▼         ▼           ▼          ▼               │
┌──────────┐ ┌──────────────────────┐                  │
│runtime   │ │    compiler-sfc      │                  │
│ -dom     │ │ (聚合所有 compiler)   │                  │
└────┬─────┘ └──────────┬───────────┘                  │
     │                   │                              │
     ▼                   ▼                              ▼
┌──────────────────────────────────────────────────────────────┐
│                          vue                                   │
│  主入口包：聚合 compiler-dom + runtime-dom + compiler-sfc      │
│  + server-renderer                                             │
│  exports: . / ./compiler-sfc / ./server-renderer / ./jsx-*    │
└──────────────────────────────────────────────────────────────┘
```

### 完整依赖表

| 包 | 内部依赖 | 外部依赖 |
| --- | --- | --- |
| `@vue/shared` | — | — |
| `@vue/reactivity` | `@vue/shared` | — |
| `@vue/compiler-core` | `@vue/shared` | `@babel/parser`, `entities`, `estree-walker`, `source-map-js` |
| `@vue/compiler-dom` | `@vue/shared`, `@vue/compiler-core` | — |
| `@vue/compiler-ssr` | `@vue/shared`, `@vue/compiler-dom` | — |
| `@vue/compiler-sfc` | `@vue/shared`, `@vue/compiler-core`, `@vue/compiler-dom`, `@vue/compiler-ssr` | `@babel/parser`, `estree-walker`, `magic-string`, `postcss`, `source-map-js` |
| `@vue/runtime-core` | `@vue/shared`, `@vue/reactivity` | — |
| `@vue/runtime-dom` | `@vue/shared`, `@vue/runtime-core`, `@vue/reactivity` | `csstype` |
| `@vue/server-renderer` | `@vue/shared`, `@vue/compiler-ssr` | — |
| `vue` | `@vue/shared`, `@vue/compiler-dom`, `@vue/runtime-dom`, `@vue/compiler-sfc`, `@vue/server-renderer` | — |
| `@vue/compat` | — | `@babel/parser`, `entities`, `estree-walker`, `source-map-js` |

---

# 四、14 个包详解

## 4.1 核心分层

Vue 3 的包设计遵循**严格的分层架构**，从底层到顶层：

```
Layer 5: vue                    ← 用户直接安装的包，聚合下层
Layer 4: compiler-sfc           ← SFC 编译器，编译时用
Layer 3: runtime-dom / server-renderer  ← 平台实现层
Layer 2: runtime-core / compiler-dom / compiler-ssr  ← 平台无关核心
Layer 1: reactivity / compiler-core  ← 独立子系统核心
Layer 0: shared                  ← 通用工具函数（零依赖）
```

## 4.2 逐包分析

### @vue/shared — 通用工具层

```
src/
├── index.ts              # 总入口
├── codeframe.ts          # 代码框错误展示
├── cssVars.ts            # CSS 变量相关
├── domAttrConfig.ts      # DOM 属性配置
├── domTagConfig.ts       # DOM 标签配置
├── escapeHtml.ts         # HTML 转义
├── general.ts            # 通用工具（hasOwn, isArray, isString 等）
├── globalsAllowList.ts   # 全局变量白名单
├── looseEqual.ts         # 宽松相等比较
├── makeMap.ts            # 快速查表 Map
├── normalizeProp.ts      # 属性名规范化
├── patchFlags.ts         # 补丁标志常量
├── shapeFlags.ts         # VNode 形状标志
├── slotFlags.ts          # 插槽标志
└── typeUtils.ts          # 类型工具
```

**特点：**
- **零外部依赖**：不依赖任何 npm 包，纯粹的 JavaScript/TypeScript 工具层
- 被其他所有 11 个包依赖，是整个 monorepo 的基石
- 包含运行时和编译时共享的常量、类型、工具函数

构建格式：`esm-bundler`、`cjs`（无 global 格式，不直接暴露给浏览器）

### @vue/reactivity — 响应式系统

```
src/
├── index.ts              # 总入口（导出所有 API）
├── effect.ts             # 核心：effect 系统 + track/trigger
├── effectScope.ts        # effectScope 作用域管理
├── dep.ts                # 依赖集合（Dep/Map/Set）
├── reactive.ts           # reactive/shallowReactive/readonly
├── ref.ts                # ref/shallowRef/toRef/toRefs/isRef/unref
├── computed.ts           # computed
├── watch.ts              # watch/watchEffect
├── baseHandlers.ts       # Proxy get/set/deleteProperty/has/ownKeys
├── collectionHandlers.ts # Map/Set/WeakMap/WeakSet 拦截
├── arrayInstrumentations.ts  # 数组方法包装（死锁预防等）
├── constants.ts          # 常量（ReactiveFlags 等）
└── warning.ts            # 警告
```

**依赖链：** `@vue/shared` only — 与 DOM、编译器完全解耦

**设计原则：** 可独立使用的响应式系统，不绑死 Vue，可被其他框架引用

构建格式：`esm-bundler`、`esm-browser`、`cjs`、`global`（`VueReactivity`）

### @vue/compiler-core — 模板编译器核心（平台无关）

```
src/
├── index.ts              # 总入口
├── compile.ts            # compile 主函数
├── parse.ts              # 模板解析（HTML → AST）
├── tokenizer.ts          # HTML 词法分析器
├── ast.ts                # AST 类型定义
├── transform.ts          # AST 转换
├── codegen.ts            # 代码生成（AST → render 函数）
├── options.ts            # 编译选项
├── errors.ts             # 编译错误
├── runtimeHelpers.ts     # 运行时辅助函数常量
├── babelUtils.ts         # Babel AST 工具
└── transforms/           # 14 个 transform 插件
    ├── transformElement.ts       # 元素处理
    ├── transformExpression.ts     # {{ expr }} 表达式处理
    ├── transformText.ts          # 文本合并
    ├── vIf.ts / vFor.ts / vOn.ts / vBind.ts / vModel.ts / vSlot.ts
    ├── vOnce.ts / vMemo.ts / cacheStatic.ts
    └── vBindShorthand.ts / transformSlotOutlet.ts /
        noopDirectiveTransform.ts
```

**依赖链：** `@vue/shared` + `@babel/parser` + `entities` + `estree-walker` + `source-map-js`

**设计原则：** 纯编译器，不依赖 DOM 或任何运行环境，可被任何渲染目标（DOM/SSR/Native）复用

构建格式：`esm-bundler`、`cjs`

### @vue/compiler-dom — DOM 模板编译器

```
src/
├── index.ts              # 总入口
├── decodeHtmlBrowser.ts  # 浏览器 HTML 实体解码
├── errors.ts             # DOM 专属编译错误
├── htmlNesting.ts        # HTML 嵌套规则检查
├── parserOptions.ts      # DOM 解析器选项
├── runtimeHelpers.ts     # DOM 运行时辅助函数
└── transforms/           # DOM 专属 transform
    ├── vModel.ts         # v-model 在 DOM 中的实现
    ├── vOn.ts            # v-on 事件修饰符
    ├── vShow.ts          # v-show 编译
    ├── vText.ts          # v-text 编译
    ├── vHtml.ts          # v-html 编译
    ├── transition.ts     # Transition 编译
    └── stringifyStatic.ts # 静态内容字符串化
```

**依赖链：** `@vue/shared` + `@vue/compiler-core`

**设计原则：** 在 compiler-core 基础上添加 DOM 专属的 transform，是最常见的编译器入口

构建格式：`esm-bundler`、`esm-browser`、`cjs`、`global`（`VueCompilerDOM`）

### @vue/compiler-ssr — SSR 编译器

```
src/
├── index.ts
├── errors.ts
├── runtimeHelpers.ts
├── ssrCodegenTransform.ts
└── transforms/
    ├── ssrTransformComponent.ts
    ├── ssrTransformElement.ts
    ├── ssrTransformSlotOutlet.ts
    ├── ssrTransformSuspense.ts
    └── ssrTransformTeleport.ts
```

**依赖链：** `@vue/shared` + `@vue/compiler-dom`

**设计原则：** 继承 compiler-dom 的 AST，添加 SSR 专属代码生成

构建格式：`cjs` only（SSR 仅 Node.js 环境，不需要 ESM bundle）

### @vue/compiler-sfc — 单文件组件编译器

```
src/
├── index.ts              # compileScript / compileStyle / compileTemplate 统一入口
├── parse.ts              # SFC 解析（<template>/<script>/<style> 分离）
├── compileScript.ts      # <script setup> 编译（1410 行，最大文件之一）
├── compileStyle.ts       # <style> 编译（含 scoped/global/module）
├── compileTemplate.ts    # <template> 编译
├── rewriteDefault.ts     # default export 重写
├── cache.ts              # 编译缓存
├── cssVars.ts            # v-bind in CSS 实现
├── context.ts            # 编译上下文
├── warn.ts               # 警告
├── shims.d.ts            # 类型补丁
├── script/
│   ├── defineProps.ts         # defineProps 编译
│   ├── defineEmits.ts         # defineEmits 编译
│   ├── defineModel.ts         # defineModel 编译
│   ├── defineOptions.ts       # defineOptions 编译
│   ├── defineExpose.ts        # defineExpose 编译
│   ├── defineSlots.ts         # defineSlots 编译
│   ├── definePropsDestructure.ts  # defineProps 解构响应式
│   └── resolveType.ts         # 类型推导（2253 行，最大文件）
├── style/
│   ├── pluginScoped.ts        # scoped CSS 处理
│   └── pluginTrim.ts          # CSS 修剪
└── template/
    ├── transformAssetUrl.ts   # 资源 URL 转换
    └── transformSrcset.ts     # srcset 处理
```

**依赖链：** 聚合了 compiler-core + compiler-dom + compiler-ssr + shared，是编译器的**顶层聚合包**

**设计原则：** 为 `vue-loader`、`@vitejs/plugin-vue`、`rollup-plugin-vue` 等构建工具提供统一的 SFC 编译能力

构建格式：`cjs`、`esm-browser`（含 browser 条件导出，使用轻量的 hash-sum 替代 crypto）

### @vue/runtime-core — 运行时核心（平台无关）

```
src/
├── index.ts
├── component.ts          # 组件实例定义与生命周期
├── componentOptions.ts   # Options API 处理
├── componentEmits.ts     # 事件发射
├── componentProps.ts     # Props 处理
├── componentSlots.ts     # Slots 处理
├── componentPublicInstance.ts  # 组件公共代理（$data/$props/$el 等）
├── vnode.ts              # VNode 创建
├── renderer.ts           # 虚拟 DOM 渲染器（createRenderer）
├── scheduler.ts          # 异步任务调度器（nextTick）
├── hydration.ts          # 客户端激活（hydrate）
├── h.ts                  # h() 函数
├── apiCreateApp.ts       # createApp API
├── apiLifecycle.ts       # 生命周期 API（onMounted 等）
├── apiInject.ts          # provide/inject
├── apiWatch.ts           # watch API
├── apiComputed.ts        # computed API（运行时封装）
├── apiAsyncComponent.ts  # defineAsyncComponent
├── apiSetupHelpers.ts    # <script setup> 运行时辅助
├── apiDefineComponent.ts # defineComponent
├── directives.ts         # 指令系统
├── errorHandling.ts      # 错误处理
├── warning.ts            # 运行时警告
├── compat/               # Vue 2 兼容层
└── helpers/              # 内部辅助工具
```

**依赖链：** `@vue/shared` + `@vue/reactivity`

**设计原则：** 平台无关的运行时，所有 DOM 操作通过抽象的 `nodeOps` 和 `patchProp` 注入

构建格式：`esm-bundler`、`cjs`

### @vue/runtime-dom — DOM 运行时

```
src/
├── index.ts              # createApp / createSSRApp + render
├── nodeOps.ts            # DOM 节点操作（createElement/insert/remove 等）
├── patchProp.ts          # DOM 属性分发（class/style/事件/prop/attr）
├── jsx.ts                # JSX 类型声明
├── apiCustomElement.ts   # defineCustomElement
├── modules/
│   ├── class.ts          # class 属性处理
│   ├── style.ts          # style 属性处理（含 CSS 变量）
│   ├── events.ts         # 事件处理（vei 事件缓存系统）
│   ├── attrs.ts          # HTML attribute 处理
│   └── props.ts          # DOM property 处理
├── directives/
│   ├── vModel.ts         # v-model 运行时
│   ├── vOn.ts            # v-on 修饰符运行时
│   └── vShow.ts          # v-show 运行时
├── components/
│   ├── Transition.ts     # <Transition> 组件
│   └── TransitionGroup.ts  # <TransitionGroup> 组件
└── helpers/
    ├── useCssModule.ts   # useCssModule
    └── useCssVars.ts     # useCssVars
```

**依赖链：** `@vue/shared` + `@vue/runtime-core` + `@vue/reactivity` + `csstype`

**设计原则：** 将 runtime-core 的抽象渲染器实例化为 DOM 渲染器，是 Web 应用的运行时入口

构建格式：`esm-bundler`、`esm-browser`、`cjs`、`global`（`VueRuntimeDOM`）

### @vue/server-renderer — SSR 渲染器

```
src/
├── index.ts
├── internal.ts
├── render.ts             # render 主逻辑
├── renderToString.ts     # renderToString
├── renderToStream.ts     # renderToStream（流式渲染）
└── helpers/
    ├── ssrRenderAttrs.ts
    ├── ssrRenderComponent.ts
    ├── ssrRenderList.ts
    ├── ssrRenderSlot.ts
    ├── ssrRenderSuspense.ts
    └── ssrRenderTeleport.ts
```

**依赖链：** `@vue/shared` + `@vue/compiler-ssr`，peerDependency: `vue`

**设计原则：** 独立的 SSR 渲染器，peer 依赖 vue 主包避免重复打包

构建格式：`esm-bundler`、`esm-browser`、`cjs`

### vue — 主入口包

```
src/
├── index.ts              # 完整版入口（含编译器和运行时）
└── runtime.ts            # 运行时版入口（不含编译器）
```

**package.json exports：**

```json
{
  ".": {
    "import": {
      "types": "./dist/vue.d.mts",
      "node": "./index.mjs",
      "default": "./dist/vue.runtime.esm-bundler.js"
    },
    "require": {
      "types": "./dist/vue.d.ts",
      "node": {
        "production": "./dist/vue.cjs.prod.js",
        "development": "./dist/vue.cjs.js",
        "default": "./index.js"
      },
      "default": "./index.js"
    }
  },
  "./server-renderer": {
    "import": { "types": "...", "default": "./server-renderer/index.mjs" },
    "require": { "types": "...", "default": "./server-renderer/index.js" }
  },
  "./compiler-sfc": {
    "import": {
      "types": "...",
      "browser": "./compiler-sfc/index.browser.mjs",
      "default": "./compiler-sfc/index.mjs"
    },
    "require": {
      "types": "...",
      "browser": "./compiler-sfc/index.browser.js",
      "default": "./compiler-sfc/index.js"
    }
  },
  "./jsx-runtime": { "types": "...", "import": "...", "require": "..." },
  "./jsx-dev-runtime": { "types": "...", "import": "...", "require": "..." },
  "./jsx": "./jsx.d.ts",
  "./dist/*": "./dist/*",
  "./package.json": "./package.json"
}
```

**构建产物（7 种格式）：**

| 格式 | 文件 | 用途 |
| --- | --- | --- |
| `esm-bundler` | `vue.esm-bundler.js` | bundle 工具（Vite/Rollup/webpack）tree-shaking |
| `esm-bundler-runtime` | `vue.runtime.esm-bundler.js` | 同上，不含编译器 |
| `esm-browser` | `vue.esm-browser.js` | 浏览器 ESM import |
| `esm-browser-runtime` | `vue.runtime.esm-browser.js` | 同上，不含编译器 |
| `cjs` | `vue.cjs.js` | Node.js CommonJS |
| `global` | `vue.global.js` | `<script>` 标签直接引用 |
| `global-runtime` | `vue.runtime.global.js` | 同上，不含编译器 |

**完整版 vs 运行时版：**
- 完整版：`index.ts` → 引入 `@vue/compiler-dom`，可用 `template` 选项
- 运行时版：`runtime.ts` → 不含编译器，需预编译模板

**依赖链：** 聚合了 compiler-dom + runtime-dom + compiler-sfc + server-renderer（用户只需安装 `vue`）

### @vue/compat — Vue 2 兼容迁移

**设计目的：** 让 Vue 2 应用平滑迁移到 Vue 3。提供 Vue 2 的废弃 API 行为模拟（如 `$on/$off/$once`、`filters`、`v-bind.sync` 等），同时输出兼容性警告。

包名 `@vue/compat`（而非 `vue`），通过构建时的别名替换实现：

```
vue → @vue/compat
@vue/compiler-dom → @vue/compiler-dom（含 compat 模式）
```

构建格式：与 vue 完全相同（7 种），`filename: "vue"` 使其产物文件名与 vue 包一致

### runtime-test — 测试用轻量渲染器

```
src/
├── index.ts
├── nodeOps.ts            # 测试用节点操作（纯 JS 对象）
├── patchProp.ts          # 测试用属性补丁
├── serialize.ts          # VNode 树序列化
└── triggerEvent.ts       # 触发事件
```

**特点：** `private: true`，不发布。为单元测试提供不依赖真实 DOM 的渲染目标。

### packages-private/ — 辅助工具

| 包 | 用途 |
| --- | --- |
| `dts-test` | 类型正确性测试（tsc 编译检查类型推导是否合理） |
| `dts-built-test` | 构建产物类型测试（测试 dist 中的 .d.ts） |
| `sfc-playground` | 在线 SFC 编译演示 |
| `template-explorer` | 模板编译结果可视化 |
| `vite-debug` | Vite 插件调试辅助 |

---

# 五、构建系统

## 5.1 工具链

```
Rollup（主打包器）
  ├── @rollup/plugin-node-resolve  # Node 模块解析
  ├── @rollup/plugin-commonjs       # CJS 转 ESM
  ├── @rollup/plugin-json          # JSON 导入
  ├── @rollup/plugin-replace       # 编译时常量替换（__DEV__, __VERSION__ 等）
  ├── @rollup/plugin-alias         # 路径别名（vue→@vue/compat 切换）
  ├── rollup-plugin-esbuild        # esbuild 高速转译 TypeScript
  ├── rollup-plugin-polyfill-node  # Node polyfill（浏览器构建用）
  └── rollup-plugin-dts            # 生成 .d.ts 声明文件

@swc/core                          # prod 构建的 minify（替代 terser，更快）
```

## 5.2 构建入口

```bash
# 构建所有公共包
node scripts/build.js

# 构建指定包（支持模糊匹配）
node scripts/build.js compiler     # 构建所有含 "compiler" 的包

# 指定输出格式
node scripts/build.js vue -f global

# 仅开发版 / 仅生产版
node scripts/build.js vue -d       # --devOnly
node scripts/build.js vue -p       # --prodOnly

# 含类型声明
node scripts/build.js vue -t       # --withTypes
```

## 5.3 构建流程

```
scripts/build.js
    │
    ├── 1. 确定目标包列表（从 packages/ 读取，或按参数过滤）
    │
    ├── 2. 对每个包：
    │   ├── 读取 package.json → buildOptions
    │   ├── 确定 formats（默认 ['esm-bundler','cjs']）
    │   ├── 执行 rollup -c
    │   │   └── rollup.config.js
    │   │       ├── 按 format 创建多个 output
    │   │       │   ├── esm-bundler  → dist/<name>.esm-bundler.js
    │   │       │   ├── esm-browser  → dist/<name>.esm-browser.js
    │   │       │   ├── cjs          → dist/<name>.cjs.js
    │   │       │   └── global       → dist/<name>.global.js (iife)
    │   │       ├── 生产环境额外创建：
    │   │       │   ├── cjs → dist/<name>.cjs.prod.js
    │   │       │   └── global → dist/<name>.global.prod.js (minified)
    │   │       └── 编译时常量替换：
    │   │           ├── __DEV__       → true/false
    │   │           ├── __VERSION__   → "3.5.35"
    │   │           ├── __BROWSER__   → true/false
    │   │           ├── __GLOBAL__    → true/false
    │   │           ├── __COMPAT__    → true/false
    │   │           └── __SSR__       → true/false
    │   │
    │   └── rollup-plugin-dts → dist/<name>.d.ts
    │
    └── 3. 输出尺寸统计（gzip/brotli）
```

### 编译时常量（Tree-shaking 的关键）

```jsx
// rollup.config.js 中的 resolveDefine()
const replacements = {
  __COMMIT__: `"${process.env.COMMIT}"`,
  __VERSION__: `"${masterVersion}"`,
  __TEST__: `false`,
  __BROWSER__: String(isBrowserBuild),
  __GLOBAL__: String(isGlobalBuild),
  __ESM_BUNDLER__: String(isBundlerESMBuild),
  __ESM_BROWSER__: String(isBrowserESMBuild),
  __CJS__: String(isCJSBuild),
  __SSR__: String(isServerRenderer),
  __COMPAT__: String(isCompatBuild),
  __FEATURE_OPTIONS_API__: String(isBundlerESMBuild),
  __FEATURE_PROD_DEVTOOLS__: String(!isProductionBuild),
  __FEATURE_SUSPENSE__: `true`,
}
```

这些常量通过 `@rollup/plugin-replace` 在编译时替换为字面量，Rollup 的 dead code elimination 会移除 `if (__DEV__) { ... }` 中的调试代码，大幅减少生产包体积。

---

# 六、版本管理

## 6.1 统一版本策略

Vue 3 的核心包（`@vue/*`）不独立发版，全部跟随 `vue` 主包的版本号。

```json
// 根 package.json
{ "version": "3.5.35" }

// 所有子包
{ "version": "3.5.35" }  // ← 与根版本完全一致
```

## 6.2 release.js 中的版本更新

```jsx
// scripts/release.js
function updateVersions(version) {
  // 1. 更新根 package.json
  updatePackage(path.resolve(__dirname, '..'), version)
  // 2. 更新所有子包 package.json
  packages.forEach(p =>
    updatePackage(getPkgRoot(p), version)
  )
}

function updatePackage(pkgRoot, version) {
  const pkg = JSON.parse(fs.readFileSync(pkgPath, 'utf-8'))
  pkg.version = version
  // workspace:* 依赖不需要在这里改 — pnpm publish 自动替换
  fs.writeFileSync(pkgPath, JSON.stringify(pkg, null, 2) + '\n')
}
```

## 6.3 workspace:* 的自动替换

这个是 pnpm 的核心能力：

```
开发时：    "@vue/shared": "workspace:*"     → 链接到 packages/shared/
发布时：    "@vue/shared": "3.5.35"          → 替换为实际版本号
```

开发者不需要手动维护跨包版本号，pnpm publish 自动完成替换。

### 但是如果用 npm/yarn 消费 `vue`？

`vue` 发布到 npm 后，其 `package.json` 中已经是具体的版本号：

```json
{
  "dependencies": {
    "@vue/shared": "3.5.35",
    "@vue/compiler-dom": "3.5.35",
    "@vue/runtime-dom": "3.5.35"
  }
}
```

用户不需要知道 workspace 的存在。

---

# 七、发布流程中的包管理

```
scripts/release.js
    │
    ├── 5. updateVersions(targetVersion)
    │   更新所有 13 个公共包的 package.json version 字段
    │
    ├── 6. pnpm run changelog
    │   生成 CHANGELOG.md
    │
    ├── 8. pnpm install
    │   更新 pnpm-lock.yaml（workspace:* 解析为当前版本）
    │
    ├── 9. git commit -m "release: v3.5.35"
    │   提交版本号变更 + CHANGELOG + lockfile
    │
    ├── 10. pnpm publish（逐个包执行）
    │   for each public package:
    │     cd packages/<pkg>
    │     pnpm publish --access public
    │     → workspace:* 自动替换为 3.5.35
    │     → catalog: 自动替换为实际外部依赖版本
    │
    └── 11. git tag v3.5.35 && git push --tags
```

### 只发布非 private 包

```jsx
// scripts/release.js
const packages = fs
  .readdirSync(path.resolve(__dirname, '../packages'))
  .filter(p => {
    const pkgRoot = path.resolve(__dirname, '../packages', p)
    if (fs.statSync(pkgRoot).isDirectory()) {
      const pkg = JSON.parse(
        fs.readFileSync(path.resolve(pkgRoot, 'package.json'), 'utf-8'),
      )
      return !pkg.private   // ← 过滤掉 private: true 的包
    }
  })
```

- 发布到 npm 的：`vue`、`@vue/shared`、`@vue/reactivity`、`@vue/runtime-core`、`@vue/runtime-dom`、`@vue/compiler-core`、`@vue/compiler-dom`、`@vue/compiler-ssr`、`@vue/compiler-sfc`、`@vue/server-renderer`、`@vue/compat`（11 个）
- 不发布的：`@vue/runtime-test`（private）、`packages-private/*`

---

# 八、TypeScript 配置

## 8.1 根 tsconfig.json

```json
{
  "compilerOptions": {
    "target": "es2016",
    "module": "esnext",
    "moduleResolution": "bundler",
    "strict": true,
    "noUnusedLocals": true,
    "experimentalDecorators": true,
    "jsx": "preserve",
    "lib": ["es2016", "dom"],
    "types": ["vitest/globals", "puppeteer", "node"]
  }
}
```

## 8.2 不依赖 Project References

与传统 monorepo 的 TypeScript 配置（如 `tsconfig.json` + `references` 指向各子包）不同，Vue 3 使用**单一 `tsconfig.json`**：

- 不做跨包类型检查分离
- `pnpm check`（`tsc --incremental --noEmit`）一次性检查整个 monorepo
- 避免了 project references 的构建顺序问题和假阴性

构建时 TypeScript 转译由 `rollup-plugin-esbuild` 完成（仅做语法转换，不做类型检查），.d.ts 生成由 `rollup-plugin-dts` 完成。

---

# 九、总结

## 设计哲学

| 原则 | 体现 |
| --- | --- |
| **严格分层** | shared → reactivity/compiler-core → runtime-core/compiler-dom → runtime-dom/compiler-sfc → vue |
| **平台无关** | compiler-core / runtime-core 不依赖任何 DOM API，通过注入实现跨平台 |
| **最小依赖** | shared 零外部依赖，每个包只声明真正需要的依赖 |
| **统一发版** | 所有 @vue/* 包版本号与 vue 一致，避免版本碎片化 |
| **编译时优化** | 大量 `__DEV__` / `__BROWSER__` 常量替换，让 Rollup 在构建时做 dead code elimination |
| **渐进增强** | runtime-only build 不含编译器（体积极小），完整版包含编译器 |

## 关键数字

| 指标 | 数值 |
| --- | --- |
| 总包数 | 14（packages）+ 5（packages-private）= 19 |
| 公开发布包 | 11 |
| 构建格式种类 | 7（esm-bundler / esm-browser / cjs / global / × runtime 变体） |
| 外部依赖数（全 monorepo） | ~50 devDependencies，运行时外部依赖仅 7 个 |
| 内部依赖最深链路 | 4 层（vue → runtime-dom → runtime-core → reactivity → shared） |
| 最大源文件 | compiler-sfc/script/resolveType.ts（2253 行） |
| pnpm catalog 管理的外部依赖 | 8 个 |

---

*文档生成时间：2026-08-05 | 源码版本：vuejs/core v3.5.35 | 包管理器：[pnpm@11.3.0](mailto:pnpm@11.3.0)*