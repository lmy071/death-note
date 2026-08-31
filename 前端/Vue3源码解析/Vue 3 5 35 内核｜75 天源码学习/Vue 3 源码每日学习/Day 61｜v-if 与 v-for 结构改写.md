# Day 61｜v-if 与 v-for 结构改写

Day: 61
完成: No
本地文件: docs/source-reading/daily/http://day-61-transform-if-for.md
核心目标: 结构指令 transform 把 Element 替换为 IfNode/ForNode
状态: 未开始
阶段: 编译器
预计小时: 3

> 阶段：编译器｜建议投入：约 3 小时｜目标：形成可以通过代码、测试和实验复验的理解。
> 

## 今日目标

- 结构指令 transform 把 Element 替换为 IfNode/ForNode
- v-if 分支 key 保证切换时 VNode identity，邻接 else/else-if 被合并
- v-for 解析 source/value/key/index 并选择 Fragment patch flag

## 源码入口

- packages/compiler-core/src/transforms/vIf.ts（本地：`packages/compiler-core/src/transforms/vIf.ts`）
- packages/compiler-core/src/transforms/vFor.ts（本地：`packages/compiler-core/src/transforms/vFor.ts`）
- packages/compiler-core/src/transform.ts（本地：`packages/compiler-core/src/transform.ts`）

## 核心机制

1. 结构指令 transform 把 Element 替换为 IfNode/ForNode
2. v-if 分支 key 保证切换时 VNode identity，邻接 else/else-if 被合并
3. v-for 解析 source/value/key/index 并选择 Fragment patch flag

不要从第一行机械读到最后一行。先确定入口输入和外部结果，再围绕上面的机制追踪分支；开发警告、compat 和复杂类型分支第一遍只做标记。

## 主调用链

```
Element with directive → createStructuralDirectiveTransform → replaceNode If/For → exit builds conditional/loop VNodeCall
```

阅读时给链路中的每个箭头补上：调用函数、关键参数、被修改的状态，以及它属于同步执行、批处理还是异步队列。

## 精读步骤

1. 打开 `packages/compiler-core/src/transforms/vIf.ts`，定位公共入口、核心数据结构和主要分派点；记录它向下调用的 2～4 个函数。
2. 打开 `packages/compiler-core/src/transforms/vFor.ts`，定位公共入口、核心数据结构和主要分派点；记录它向下调用的 2～4 个函数。
3. 打开 `packages/compiler-core/src/transform.ts`，定位公共入口、核心数据结构和主要分派点；记录它向下调用的 2～4 个函数。
4. 全仓搜索今日核心函数的调用方，分别找出至少一个生产者和消费者。
5. 对照测试，用边界用例修正自己的初始推断。

## 动手实验

1. 画 v-if/v-else 与 v-for AST
2. 比较 stable/keyed/unkeyed v-for codegen
3. 跟踪 v-for scope 变量对表达式前缀化

实验必须记录“输入、预期、实际结果、源码解释”，只记录最终输出不算完成。

## 测试与反证

- packages/compiler-core/**tests**/transforms/vIf.spec.ts（本地：`packages/compiler-core/__tests__/transforms/vIf.spec.ts`）
- packages/compiler-core/**tests**/transforms/vFor.spec.ts（本地：`packages/compiler-core/__tests__/transforms/vFor.spec.ts`）

```bash
pnpm vitest packages/compiler-core/__tests__/transforms/vIf.spec.ts
pnpm vitest packages/compiler-core/__tests__/transforms/vFor.spec.ts
```

若当前仓库基线阻止测试启动，记录首个环境/语法错误和阻断链，不要把它误判成今日主题的行为错误。

## 闭卷验收

1. 为什么结构指令必须改写树？
2. if branch key 防止什么复用错误？
3. v-for source 稳定性如何影响 Fragment flag？

## 今日完成标准

- [ ]  能不看源码画出主调用链。
- [ ]  能解释至少三个关键分支及其设计权衡。
- [ ]  完成全部实验，并阅读对应测试中的边界案例。
- [ ]  写出一个最小复刻、伪代码或状态转换表。
- [ ]  将仍不确定的问题标注为“事实缺口”或“设计取舍”。