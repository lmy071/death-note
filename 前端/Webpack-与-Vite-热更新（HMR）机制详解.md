# Webpack 与 Vite 热更新（HMR）机制详解

# Webpack 与 Vite 热更新（HMR）机制详解

## 一、Webpack HMR 全流程

### 1.1 架构总览

```
┌─────────────────────────────────────────────────────┐
│                    webpack-dev-server                │
│                                                      │
│  ┌──────────┐     ┌──────────────┐    ┌───────────┐ │
│  │  文件监听  │ ──→ │  重新编译打包  │ ──→ │ WebSocket │──→ 浏览器 │
│  │ (watcher) │     │ (compiler)   │    │  Server   │ │
│  └──────────┘     └──────────────┘    └───────────┘ │
│                         │                     ↑      │
│                         │  hot-update.json     │      │
│                         │  hot-update.js      HTTP     │
│                         ↓                     │      │
│                    ┌──────────┐               │      │
│                    │ 文件系统  │←─ 浏览器 fetch ────────│
│                    └──────────┘                       │
└─────────────────────────────────────────────────────┘
```

### 1.2 第一步：文件监听

- **底层**：Webpack 内部使用 `Watchpack`（封装 Node.js `fs.watch`）
- **防抖**：`aggregateTimeout: 300`（300ms 内的多次改动合并为一次编译）
- **轮询降级**：Docker / NFS 等场景下 `poll: true` 降级为定时轮询
- **触发**：文件变化 → `compiler.watching.invalidate()` → 重新走完整编译流程 `make → seal → emit`

```jsx
// webpack 内部调用链
compiler.watch({
  aggregateTimeout: 300,
  poll: false,                    // 默认使用 fs.watch，不轮询
  ignored: /node_modules/,
}, (err, stats) => { ... });
```

### 1.3 第二步：增量编译 + 生成补丁文件

Webpack 执行**增量编译**，只重新构建变更模块及其依赖链，输出两个关键文件：

#### hot-update.json — 变更清单

```json
{
  "c": ["main"],              // 哪些 chunk 变了
  "r": [],                    // 没变的 runtime chunk
  "m": ["../../src/a.js"]     // 哪些模块变了
}
```

#### hot-update.js — 变更代码

```jsx
webpackHotUpdate("main", {
  "../../src/a.js": function(module, exports, __webpack_require__) {
    // 新的模块代码...
  }
});
```

> 文件中的哈希由 `compilation.hash` 生成，每次编译都会变化，防止浏览器缓存旧文件。
> 

### 1.4 第三步：WebSocket 推送通知

```jsx
// 在 compiler.hooks.done 中推送
compiler.hooks.done.tap('webpack-dev-server', (stats) => {
  this.sockWrite(this.sockets, 'hash', stats.hash);
  this.sockWrite(this.sockets, 'ok');
});
```

消息类型说明：

| 消息 type | 含义 |
| --- | --- |
| `hash` | 新编译的 hash 值 |
| `ok` | 编译成功，可以拉取更新了 |
| `invalid` | 文件变了，正在编译中 |
| `still-ok` | 编译完成但没实质更新 |
| `warnings` | 编译有 warning |
| `errors` | 编译失败 |

### 1.5 第四步：浏览器端 hotApply（核心）

浏览器收到 `hash` + `ok` 后的执行链：

```jsx
hotDownloadManifest()    // ① fetch hot-update.json → 知道哪些模块变了
  ↓
hotDownloadUpdateChunk() // ② fetch hot-update.js → script 标签注入
  ↓
hotAddUpdateChunk()      // ③ 把新模块注册到 __webpack_modules__ 里
  ↓
hotUpdateDownloaded()    // ④ 遍历变更模块，沿依赖树向上找 HMR boundary
  ↓
  ├── 找到 module.hot.accept() → 局部热更新
  └── 找不到 accept → 整页 location.reload()
```

### 1.6 HMR Boundary（HMR 边界）

```jsx
// src/index.js
import a from './a';
a();

// ✅ 注册了 accept → 这是 HMR boundary → 局部更新
if (module.hot) {
  module.hot.accept('./a', () => {
    // a.js 更新后执行的回调
  });
}
```

**规则**：变更模块的父模块链上如果没有任何 `module.hot.accept()`，Webpack 退化为 full reload。

---

## 二、Vite HMR 全流程

### 2.1 架构总览

```
┌───────────────────────────────────────────────────────┐
│                     Vite Dev Server                    │
│                                                        │
│  ┌──────────┐    ┌──────────────┐    ┌──────────────┐ │
│  │ chokidar  │───→│ ModuleGraph  │───→│  WebSocket   │ │─── @vite/client
│  │ 文件监听   │    │ 依赖图分析   │    │  推送更新     │ │    (浏览器)
│  └──────────┘    └──────────────┘    └──────────────┘ │
│                          │                  ↑         │
│                          │  按需即时编译      │         │
│                          ↓   缓存到内存       │         │
│                     ┌─────────┐              │         │
│                     │ 内存缓存  │──HTTP fetch──│         │
│                     │ (不落盘)  │                       │
│                     └─────────┘                       │
└───────────────────────────────────────────────────────┘
```

### 2.2 第一步：文件监听（chokidar）

```tsx
// Vite 直接使用 chokidar，比 Node 原生 fs.watch 可靠得多
const watcher = chokidar.watch(root, {
  ignored: ['**/node_modules/**', '**/.git/**'],
  ignoreInitial: true,
});

watcher.on('change', async (file) => {
  moduleGraph.onFileChange(file);      // 标记失效节点
  await handleHMRUpdate(file, server); // 执行 HMR
});
```

> Vite 只在**初次请求某个模块时**才将其加入监听列表（按需监听），不像 Webpack 一启动就全量监听。
> 

### 2.3 第二步：ModuleGraph 依赖图（核心数据结构）

```tsx
class ModuleNode {
  url: string;                     // /src/App.vue
  file: string;                    // /project/src/App.vue
  importers: Set<ModuleNode>;      // 谁依赖了"我"（父节点）
  importedModules: Set<ModuleNode>;// "我"依赖了谁（子节点）
  transformResult: TransformResult;// 编译结果缓存
}

class ModuleGraph {
  fileToModulesMap: Map<string, Set<ModuleNode>>;
  urlToModuleMap: Map<string, ModuleNode>;
}
```

**变更传播链路**：

```
a.js 变更
  → moduleGraph.getModulesByFile('a.js')  → 找到 ModuleNode(a)
  → ModuleNode(a).importers               → 找到所有 import a 的模块
  → 递归向上，逐层找 import.meta.hot.accept()  → 确定更新边界
```

### 2.4 第三步：按需编译（零中间文件）

**这是 Vite 和 Webpack 最根本的区别**——Vite 不打包：

| 阶段 | Webpack | Vite |
| --- | --- | --- |
| 初次请求 | 打包成 chunk → 返回 bundle | 即时 esbuild 转译 → 返回原生 ESM |
| 文件变更 | `make → seal → emit` 产出 `hot-update.js` | 重新转译变更文件，放内存 |
| 浏览器获取 | `fetch hot-update.js` → `script` 注入 | `import('/src/a.js?t=新时间戳')` |

**没有中间文件，没有 JSON manifest，没有 chunk 概念。** ESM 天然按需加载即是增量更新。

### 2.5 第四步：WebSocket 推送更新指令

```tsx
// packages/vite/src/node/server/hmr.ts
const updates = [
  {
    type: 'js-update',
    path: '/src/a.js',
    acceptedPath: '/src/a.js',
    timestamp: Date.now(),
  },
  {
    type: 'css-update',
    path: '/src/style.css',
    timestamp: Date.now(),
  },
];

ws.send({ type: 'update', updates });
```

| 更新类型 | 处理方式 |
| --- | --- |
| `js-update` | 重新 `import(url + '?t=xxx')`，走 accept 回调 |
| `css-update` | 直接替换 `<style>` 标签内容，不丢 JS 状态 |
| `full-reload` | `location.reload()` |

### 2.6 第五步：浏览器端 @vite/client

```tsx
// @vite/client/client.ts 简化
socket.addEventListener('message', async ({ data }) => {
  const { type, updates } = JSON.parse(data);

  if (type === 'update') {
    for (const update of updates) {
      if (update.type === 'js-update') {
        // 重新 import 新模块（?t= 破坏缓存）
        const newModule = await import(update.path + `?t=${update.timestamp}`);

        // 执行 accept 回调
        hotModulesMap.get(update.path)
          ?.forEach(({ callbacks }) =>
            callbacks.forEach(cb => cb(newModule))
          );
      }
      else if (update.type === 'css-update') {
        // 直接替换 <style> 标签，极快且不丢状态
        updateStyle(update.path, update.timestamp);
      }
      else if (update.type === 'full-reload') {
        location.reload();
      }
    }
  }
});
```

---

## 三、Webpack vs Vite HMR 核心差异

| 维度 | Webpack | Vite |
| --- | --- | --- |
| **文件监听** | `Watchpack`（封装 fs.watch） | `chokidar`（更可靠、更可控） |
| **监听策略** | 启动即全量监听 | 按需监听（首次请求时加入） |
| **源码 → 浏览器** | 打包成 chunk 文件 → HTTP | 按需 esbuild 转译，浏览器直接 import ESM |
| **变更后处理** | 重新走 `make → seal → emit` 打包 | 只重新转译变更文件，放内存 |
| **中间文件** | `hot-update.json` + `hot-update.js` | **零中间文件** |
| **通知方式** | WebSocket 推 `hash` + `ok` | WebSocket 推 `update` 列表（含类型和路径） |
| **浏览器获取** | `fetch` hot-update.json → `fetch` hot-update.js → script 注入 | 原生 `import(url + '?t=xxx')` 重新请求 |
| **CSS 热更新** | 同 JS 流程，通过 `module.hot.accept` 替换 `<style>` | 直接替换 `<style>` 标签内容，极快且不丢状态 |
| **React/Vue 组件** | 依赖 `react-refresh` / `vue-loader` 注入边界 | 内置 Fast Refresh，babel/swc 插件注入 |
| **未找到边界** | 整页 `location.reload()` | `full-reload` → `location.reload()` |
| **编译速度** | 增量打包，大型项目 1~5 秒 | esbuild 即时转译，毫秒级 |
| **依赖图** | 打包时的依赖分析 | 运行时的 `ModuleGraph` 数据结构 |

---

## 四、流程对比图

### Webpack HMR

```
文件变更
  → Watchpack 检测
  → compiler 增量打包 (make → seal → emit)
  → 生成 hot-update.json + hot-update.js
  → WebSocket 推送 { hash, ok }
  → 浏览器 fetch hot-update.json → fetch hot-update.js
  → webpackHotUpdate 函数注册新模块到 __webpack_modules__
  → hotApply 沿依赖树向上找 module.hot.accept()
    ├── 找到 → 执行 accept 回调 → 局部热更新
    └── 没找到 → location.reload() → 整页刷新
```

### Vite HMR

```
文件变更
  → chokidar 检测
  → ModuleGraph.onFileChange() 标记失效节点
  → 沿 importers 递归向上找 import.meta.hot.accept() 边界
  → esbuild 重新转译变更文件（放内存）
  → WebSocket 推送 { type: 'update', updates: [...] }
  → 浏览器收到后
    ├── js-update: import(url + ?t=xxx) → 执行 accept 回调
    ├── css-update: 直接替换 <style> 标签
    └── full-reload: location.reload()
```

---

## 五、一句话总结

| **Webpack** | 走 “重新打包 → 生成补丁文件 → 注入 → 替换” 的 Bundle 思维 |
| --- | --- |
| **Vite** | 走 “源文件变了就重新转译 → 浏览器重新 import → 替换模块” 的 ESM 原生思维 |

Vite HMR 比 Webpack 快得多的根本原因：**它不需要打包这一步**。ESM 的按需加载就是天然的增量更新，`import(url + '?t=xxx')` 一行代码搞定，无需 `hot-update.json` + `hot-update.js` 中间文件，无需 chunk diff 计算。