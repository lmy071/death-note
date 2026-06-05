# Vue 3 源码启动与调试指南

> 针对 https://github.com/lmy071/vue3 (Vue.js core 源码)

---

## 环境准备

```bash
# 克隆仓库
git clone https://github.com/lmy071/vue3.git
cd vue3

# 安装依赖（Vue 3 使用 pnpm 管理 monorepo）
pnpm install

# 构建源码
pnpm build
```

---

## 启动开发环境

### 1. 运行测试用例（推荐）

```bash
# 运行单元测试（使用 Vitest）
pnpm test

# 运行特定包测试
pnpm test packages/reactivity

# 带 UI 的测试（交互式调试）
pnpm test -- --ui
```

### 2. 启动示例项目

```bash
# 进入示例目录
cd packages/vue/examples/

# 启动本地服务器（使用 Vite）
npx vite

# 或指定示例
npx vite ./classic/todomvc
```

### 3. 使用 Playground

```bash
# Vue 3 源码自带 playground
cd packages/vue/examples/composition
npx vite
```

---

## 源码调试方法

### VS Code 调试配置

创建 `.vscode/launch.json`:

```json
{
  "version": "0.2.0",
  "configurations": [
    {
      "type": "node",
      "request": "launch",
      "name": "Debug Tests",
      "runtimeExecutable": "pnpm",
      "runtimeArgs": ["test", "--", "--reporter=verbose"],
      "console": "integratedTerminal",
      "internalConsoleOptions": "neverOpen"
    },
    {
      "type": "chrome",
      "request": "launch",
      "name": "Debug Browser",
      "url": "http://localhost:5173",
      "webRoot": "${workspaceFolder}",
      "sourceMapPathOverrides": {
        "webpack:///packages/*": "${webRoot}/packages/*"
      }
    }
  ]
}
```

### 关键断点位置

| 模块 | 文件路径 | 调试重点 |
|------|----------|----------|
| **Reactivity** | `packages/reactivity/src/reactive.ts` | `reactive()`, `ref()` 实现 |
| **Reactivity** | `packages/reactivity/src/effect.ts` | 依赖收集、触发更新 |
| **Runtime Core** | `packages/runtime-core/src/renderer.ts` | 虚拟 DOM 渲染逻辑 |
| **Runtime Core** | `packages/runtime-core/src/component.ts` | 组件实例化 |
| **Compiler Core** | `packages/compiler-core/src/parse.ts` | 模板解析 |
| **Compiler Core** | `packages/compiler-core/src/codegen.ts` | 代码生成 |

### 浏览器调试技巧

```js
// 在控制台访问 Vue 内部 API
__VUE__

// 查看当前组件实例
__VUE_INSPECT__

// 追踪响应式依赖
Vue.devtools?.inspect?.()
```

---

## 源码结构

```
packages/
├── reactivity/          # 响应式系统 (ref, reactive, effect)
├── runtime-core/        # 运行时核心 (vnode, component, scheduler)
├── runtime-dom/         # DOM 运行时 (DOM API 操作)
├── compiler-core/       # 编译器核心 (parse, transform, codegen)
├── compiler-dom/        # DOM 编译器 (DOM 特定优化)
├── compiler-sfc/        # SFC 编译器 (.vue 文件处理)
├── vue/                 # 完整构建入口
└── shared/              # 共享工具函数
```

---

## 常用调试命令

```bash
# 构建特定包
pnpm build reactivity

# 监听模式构建
pnpm build --watch

# 运行类型检查
pnpm check

# 代码格式化
pnpm format

# 代码检查
pnpm lint
```

---

## 调试响应式系统

```js
// 在测试文件中添加调试代码
import { reactive, effect } from '@vue/reactivity'

const state = reactive({ count: 0 })

effect(() => {
  debugger  // 断点：观察依赖收集
  console.log('count:', state.count)
})

state.count++  // 断点：观察触发更新
```

---

## 参考资源

- [Vue 3 源码解读](https://vuejs.org/guide/extras/rendering-mechanism.html)
- [响应式原理](https://vuejs.org/guide/extras/reactivity-in-depth.html)
- [贡献指南](https://github.com/vuejs/core/blob/main/.github/contributing.md)
