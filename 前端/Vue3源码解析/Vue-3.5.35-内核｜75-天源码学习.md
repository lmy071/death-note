# Vue 3.5.35 内核｜75 天源码学习

<aside>
🎯

**目标**：用连续 75 个学习日完整理解 Vue 3.5.35 内核。每天约 3 小时，总投入约 225 小时；不使用周次。

</aside>

## 使用方式

1. 每次只打开一个 Day 条目。
2. 完成源码入口、主调用链、动手实验、测试反证和闭卷验收。
3. 未通过当日验收就顺延，不按自然周赶进度。
4. 每 5 天闭卷画一次累计调用链，但不建立周任务。

## 阶段地图

| 阶段 | Day | 主题 |
| --- | --- | --- |
| 工程基线 | 01–04 | 仓库、构建、测试与可执行基线 |
| 共享协议 | 05–07 | 通用工具、规范化、安全与 Flags |
| 响应式系统 | 08–20 | Proxy、Dep/Link、effect、ref、computed、watch |
| 运行时与渲染器 | 21–45 | VNode、组件、scheduler、renderer、diff、hydration |
| DOM 与内置组件 | 46–55 | 真实 DOM、指令、Transition、KeepAlive、Teleport、Suspense |
| 编译器 | 56–66 | AST、Tokenizer、Parser、Transform、Codegen |
| SFC | 67–70 | Descriptor、compileScript、宏、样式与资源转换 |
| SSR | 71–73 | SSR 编译、字符串/流式渲染、Hydration |
| 工程复盘 | 74–75 | 发布形态、HMR、Devtools、Compat 与总验收 |

## 最终主链

```
响应式：Proxy/ref → track/Dep/Link → trigger/batch → effect scheduler
更新：state write → queueJob → componentUpdateFn → renderComponentRoot → patch
挂载：createApp → render → patch → mountComponent → setupRenderEffect → host ops
编译：template → tokenizer/parser → transform → codegen → render function
SFC：descriptor → compileScript/template/style → component module
SSR：compiler-ssr → server renderer/buffer/stream → HTML → hydrateNode
```

## 最终验收

- [ ]  闭卷画出包依赖图和六条主调用链。
- [ ]  手算 keyed diff 与 LIS，并解释 compiler flags 如何驱动 renderer 快路径。
- [ ]  完成 mini-reactivity、mini-renderer 和 1,500～3,000 行 mini-vue 或等价实现。
- [ ]  能从任意公开 API 在 10 分钟内定位核心实现、消费者与测试。

[Vue-3-源码每日学习](<Vue-3.5.35-内核｜75-天源码学习/Vue-3-源码每日学习.csv>)