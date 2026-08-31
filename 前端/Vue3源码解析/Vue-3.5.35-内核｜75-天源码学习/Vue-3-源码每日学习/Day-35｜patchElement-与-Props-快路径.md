# Day 35｜patchElement 与 Props 快路径

Day: 35
完成: No
本地文件: docs/source-reading/daily/http://day-35-patch-element.md
核心目标: dynamicChildren 可进入 patchBlockChildren
状态: 未开始
阶段: 渲染器
预计小时: 3

> 阶段：渲染器｜建议投入：约 3 小时｜目标：形成可以通过代码、测试和实验复验的理解。
> 

## 今日目标

- dynamicChildren 可进入 patchBlockChildren
- 正数 PatchFlags 将更新缩小到 class/style/dynamicProps/text
- 无优化信息时 patchProps 做全量新增、更新与删除

## 源码入口

- packages/runtime-core/src/renderer.ts（本地：`packages/runtime-core/src/renderer.ts`）
- packages/shared/src/patchFlags.ts（本地：`packages/shared/src/patchFlags.ts`）

## 核心机制

1. dynamicChildren 可进入 patchBlockChildren
2. 正数 PatchFlags 将更新缩小到 class/style/dynamicProps/text
3. 无优化信息时 patchProps 做全量新增、更新与删除

不要从第一行机械读到最后一行。先确定入口输入和外部结果，再围绕上面的机制追踪分支；开发警告、compat 和复杂类型分支第一遍只做标记。

## 主调用链

```
processElement(update) → patchElement → patchBlockChildren/patchChildren → patch flags 或 full props diff → hooks
```

阅读时给链路中的每个箭头补上：调用函数、关键参数、被修改的状态，以及它属于同步执行、批处理还是异步队列。

## 精读步骤

1. 打开 `packages/runtime-core/src/renderer.ts`，定位公共入口、核心数据结构和主要分派点；记录它向下调用的 2～4 个函数。
2. 打开 `packages/shared/src/patchFlags.ts`，定位公共入口、核心数据结构和主要分派点；记录它向下调用的 2～4 个函数。
3. 全仓搜索今日核心函数的调用方，分别找出至少一个生产者和消费者。
4. 对照测试，用边界用例修正自己的初始推断。

## 动手实验

1. 用动态 class/id/text 模板观察不同分支
2. 手写 render function 对比 full diff
3. 验证旧 FULL_PROPS flag 如何合入新节点

实验必须记录“输入、预期、实际结果、源码解释”，只记录最终输出不算完成。

## 测试与反证

- packages/runtime-core/**tests**/rendererElement.spec.ts（本地：`packages/runtime-core/__tests__/rendererElement.spec.ts`）
- packages/runtime-core/**tests**/rendererOptimizedMode.spec.ts（本地：`packages/runtime-core/__tests__/rendererOptimizedMode.spec.ts`）

```bash
pnpm vitest packages/runtime-core/__tests__/rendererElement.spec.ts
pnpm vitest packages/runtime-core/__tests__/rendererOptimizedMode.spec.ts
```

若当前仓库基线阻止测试启动，记录首个环境/语法错误和阻断链，不要把它误判成今日主题的行为错误。

## 闭卷验收

1. PatchFlag 何时能跳过 props 全扫描？
2. dynamicProps 为什么不必处理删除未知 key？
3. HMR 更新为何可能关闭优化？

## 今日完成标准

- [ ]  能不看源码画出主调用链。
- [ ]  能解释至少三个关键分支及其设计权衡。
- [ ]  完成全部实验，并阅读对应测试中的边界案例。
- [ ]  写出一个最小复刻、伪代码或状态转换表。
- [ ]  将仍不确定的问题标注为“事实缺口”或“设计取舍”。