# Vue 3 编译器核心管线深度解析

> 基于 `vuejs/core` 仓库（v3.5.35）源码分析。
> 
> 
> 涵盖：`compiler-core` 的 parse → transform → generate 三阶段完整流程。
> 

---

# 一、编译器总览

## 1.1 编译入口：baseCompile

```tsx
// compile.ts
export function baseCompile(source: string | RootNode, options: CompilerOptions = {}): CodegenResult {
  // 1. 配置解析（prefixIdentifiers、scopeId、isTS等）
  // 2. Parse: 模板字符串 → AST
  const ast = isString(source) ? baseParse(source, resolvedOptions) : source
  // 3. Transform: AST 优化 → 优化后的 AST
  const [nodeTransforms, directiveTransforms] = getBaseTransformPreset(prefixIdentifiers)
  transform(ast, extend({}, resolvedOptions, {
    nodeTransforms: [...nodeTransforms, ...(options.nodeTransforms || [])],
    directiveTransforms: extend({}, directiveTransforms, options.directiveTransforms || {}),
  }))
  // 4. Generate: AST → JavaScript 渲染函数
  return generate(ast, resolvedOptions)
}
```

## 1.2 三阶段 Pipeline

```
模板字符串
    │
    ▼
┌─────────────────────────────────────────────────────────┐
│ PHASE 1: Parse (parser.ts + tokenizer.ts)              │
│                                                         │
│ Tokenizer (状态机)  →  token 流  →  AST 树              │
│                                                         │
│ 输入: <div>{{ msg }}</div>                             │
│ 输出: RootNode { children: [ElementNode, ...] }         │
│                                                         │
│ 状态机: 49 个状态（Text/InterpolationOpen/InTagName...） │
│ 字符级处理: 0x3c='<'→BeforeTagName, 0x7b='{'→Interp... │
│ SFC 模式: root 级非 template 标签 → RAWTEXT            │
│ 实体解码: entities/decode 库（浏览器用 DOM 解码）        │
│ RCDATA: <title>/<textarea> 内解析实体和插值              │
│ RAWTEXT: <script>/<style> 内跳过解析，直找 </tag>       │
└──────────────────┬──────────────────────────────────────┘
                   ▼
┌─────────────────────────────────────────────────────────┐
│ PHASE 2: Transform (transform.ts + transforms/*.ts)     │
│                                                         │
│ 2.1 深度优先遍历 AST                                     │
│ 2.2 NodeTransform 序列（17个，按序执行）                  │
│     ├── 结构型: v-once/v-if/v-memo/v-for/v-slot         │
│     ├── 表达式: transformExpression                     │
│     ├── 元素型: transformElement                        │
│     └── 文本型: transformText                           │
│ 2.3 DirectiveTransform（on/bind/model，按指令名分发）     │
│                                                         │
│ 每个节点: enter → transforms → children → exit          │
│ 出口钩子: 收集后逆序执行                                  │
│ 类型提升: ConstantTypes (NOT_CONSTANT→SKIP_PATCH→       │
│           CAN_CACHE→CAN_STRINGIFY)                      │
│ hoists: 静态提升（数组存储，-1/0/1 分块索引）             │
│ cacheHandlers: 事件缓存（_cache[0] || $event）           │
│ PatchFlags: 编译时计算运行时优化位标记                    │
│ Block Tree: 动态节点收集 + openBlock/createBlock         │
│ prefixIdentifiers: _ctx.xxx / _cache / $setup            │
└──────────────────┬──────────────────────────────────────┘
                   ▼
┌─────────────────────────────────────────────────────────┐
│ PHASE 3: Generate (codegen.ts)                          │
│                                                         │
│ 递归遍历优化后的 AST → 拼接字符串生成 JS 代码              │
│                                                         │
│ 模式: module / function                                 │
│ module: import + export default render                  │
│ function: const { x } = Vue + return function render    │
│                                                         │
│ Preamble: hoisted 静态节点/VNode                       │
│ render 函数体: node.codegenNode → genNode() 递归        │
│                                                         │
│ 运行时 helpers: createVNode/createBlock/openBlock/      │
│   createTextVNode/toDisplayString/withDirectives...     │
│                                                         │
│ Source Map: source-map-js 增量映射（每个 push 加映射项） │
└─────────────────────────────────────────────────────────┘
    │
    ▼
JavaScript 渲染函数字符串
```

---

# 二、Phase 1: Tokenizer（词法分析）

## 2.1 状态机设计

Tokenizer 是 Vue 3 模板编译器的最底层基础设施，改编自 htmlparser2（MIT License）。它是一个**单字符级状态机**，共 49 个状态。

```
核心状态流转：

  Text ──→ '<' ──→ BeforeTagName
    │               ├── isTagStartChar → InTagName ──→ endOfTagSection → handleTagName
    │               ├── '/' → BeforeClosingTagName → InClosingTagName
    │               ├── '!' → BeforeDeclaration（注释/DOCTYPE/CDATA）
    │               └── '?' → InProcessingInstruction
    │
    ├── '{{' ──→ InterpolationOpen → Interpolation → '}}' → InterpolationClose → Text
    │
    └── '&' ──→ InEntity → entityDecoder → Text

  InTagName ──→ '>'或空格 ──→ BeforeAttrName
    ├── 属性名 → InAttrName / InDirName (v-)
    │   ├── ':' → InDirArg
    │   ├── '[' → InDirDynamicArg
    │   └── '.' → InDirModifier
    ├── '=' → BeforeAttrValue → InAttrValueDq/Sq/Nq
    ├── '/' → InSelfClosingTag
    └── '>' → opentagend → InRCDATA 或 Text

  Special Tags:
    's' (BeforeSpecialS) → 匹配 'cript'/'tyle' → startSpecial → InRCDATA
    't' (BeforeSpecialT) → 匹配 'itle'/'extarea' → startSpecial → InRCDATA
    SFC root: 非 template 标签全部 RAWTEXT
```

## 2.2 RCDATA vs RAWTEXT

| 模式 | 内容 | 解析行为 | 结束条件 |
| --- | --- | --- | --- |
| **RCDATA** | `<title>`, `<textarea>` | 解析实体 `&amp;`、解析插值 `{{ }}` | 遇到 `</title` / `</textarea` |
| **RAWTEXT** | `<script>`, `<style>` | **不解析任何内容**（包括实体），逐字符比对 end tag | 遇到 `</script` / `</style` |
| **SFC Root** | `<script>`, `<style>`, `<custom>` | RAWTEXT（跳过所有解析） | 遇到 `</tagName` |

**RCDATA 中的插值处理**：在 `<textarea>{{ count }}</textarea>` 中，Tokenzier 在 InRCDATA 状态会额外检查 `{` 字符并切换到 InterpolationOpen 状态。

## 2.3 实体解码

```
非浏览器: entities/decode 库 → EntityDecoder → htmlDecodeTree
浏览器: DOM 元素 innerHTML 解码（tree-shaking 掉 entities 依赖）
```

```tsx
// InEntity 状态 → 调用 entityDecoder.write(buffer, index)
// 解码完成 → 回调 emitCodePoint → ontextentity / onattribentity
```

## 2.4 字符码优化

所有比较使用 `CharCodes` 枚举（数值），而非字符串：

```tsx
enum CharCodes {
  Lt = 0x3c,   // '<' → 触发标签开始
  Gt = 0x3e,   // '>' → 标签结束
  Amp = 0x26,  // '&' → 实体开始
  // ...
}
```

序列匹配使用 `Uint8Array`（`Sequences.ScriptEnd` 等），比较时用 `(c | 0x20)` 做大小写不敏感（ASCII trick：大写字母 bit5 清零 = 小写）。

## 2.5 fastForwardTo

当 tokenizer 在 RCDATA 中等待下一个 `<` 时，跳过逐字符状态机，直接扫描 buffer：

```tsx
private fastForwardTo(c: number): boolean {
  while (++this.index < this.buffer.length) {
    if (this.buffer.charCodeAt(this.index) === c) return true
  }
  this.index = this.buffer.length - 1
  return false
}
```

这是整个 tokenizer 中最大的性能优化点——大部分模板中 `<script>` 和 `<style>` 的内容可以一次性跳过。

## 2.6 行号/列号追踪

```tsx
// 换行时记录位置
if (c === CharCodes.NewLine) {
  this.newlines.push(this.index)
}

// 获取行列：二分查找最近换行
getPos(index: number): Position {
  // newlines.length > 100 → 二分查找
  // 否则 → 线性反向扫描
}
```

---

# 三、Phase 1: Parser（语法分析）

## 3.1 架构

Parser 使用 Tokenizer 的回调接口（Callbacks）构建 AST：

```
Tokenzier.parse(input)
    │
    ├── ontext(start, end)        → addNode(TextNode)
    ├── oninterpolation(start, end) → addNode(InterpolationNode)
    ├── onopentagname(start, end) → 创建 ElementNode
    ├── onattribname/onattribend  → 创建 AttributeNode/DirectiveNode
    ├── onopentagend(end)         → endOpenTag（入栈/自闭合）
    ├── onclosetag(start, end)    → 出栈匹配
    ├── oncomment(start, end)     → addNode(CommentNode)
    └── onend()                   → 完成解析
```

## 3.2 标签栈

```tsx
const stack: ElementNode[] = []

// 开标签入栈
function endOpenTag(end: number) {
  // 自闭合标签不 push
  // 否则 push 到 stack 并设为 currentOpenTag
}

// 闭标签出栈
function onCloseTag(name: string) {
  // 从栈顶向下找匹配的标签（处理隐式闭合，如 <p>隐式闭合前一个<p>）
  // found → 出栈到匹配位置
  // not found → 报错
}
```

## 3.3 属性解析

```
v-bind:name.modifier="value"
│     │    │        │
│     │    │        └── InAttrValueDq/Sq/Nq → onattribdata
│     │    └── InDirModifier → ondirmodifier
│     └── InDirArg → ondirarg
└── InDirName → ondirname

普通属性: InAttrName → onattribname
动态参数: InDirDynamicArg (方括号内)
```

## 3.4 表达式解析

Interpolation 内的表达式由 **@babel/parser** 解析：

```tsx
// parser.ts
function createExp(content: string, isStatic: boolean, loc: SourceLocation) {
  // isStatic → 常量表达，不解析
  // 否则 → parseExpression(content, babelOptions) → AST
  // babelOptions: { plugins: ['typescript', ...expressionPlugins] }
  return createSimpleExpression(content, isStatic, loc, constType)
}
```

双大括号中的 JavaScript 表达式会被 @babel/parser 的 `parseExpression` 解析为 AST，然后存储到 `SimpleExpressionNode.ast`。这个 AST 在 transform 阶段由 `processExpression` 消费，用于：
- **前缀标识符**：`msg` → `_ctx.msg`
- **常量检测**：`CAN_STRINGIFY` → 可字符串化
- **作用域分析**：追踪函数参数中声明的标识符

## 3.5 AST 节点类型

完整的 Vue 模板 AST 节点类型（`NodeTypes` 枚举，30 种）：

| 类别 | 节点 | 说明 |
| --- | --- | --- |
| **模板节点** | ROOT, ELEMENT, TEXT, COMMENT | 基本模板结构 |
| **表达式** | SIMPLE_EXPRESSION, INTERPOLATION, COMPOUND_EXPRESSION | 插值和复合表达式 |
| **结构指令** | IF, IF_BRANCH, FOR | v-if 链、v-for |
| **属性** | ATTRIBUTE, DIRECTIVE | 静态属性和指令 |
| **TextCall** | TEXT_CALL | 合并后的文本节点 |
| **代码生成** | VNODE_CALL | 渲染函数 VNode 调用 |
| **JS AST** | JS_CALL/OBJECT/PROPERTY/ARRAY/FUNCTION/CONDITIONAL/CACHE_EXPRESSION | 生成 JS 代码用的简化 AST |
| **SSR** | JS_BLOCK_STATEMENT/TEMPLATE_LITERAL/IF_STATEMENT/ASSIGNMENT/SEQUENCE/RETURN | SSR 专用节点 |

### ElementTypes 四种

```
ELEMENT    → PlainElementNode    (tagType: ELEMENT)    → createElementVNode
COMPONENT  → ComponentNode       (tagType: COMPONENT)  → createVNode(resolveComponent())
SLOT       → SlotOutletNode      (tagType: SLOT)       → renderSlot()
TEMPLATE   → TemplateNode        (tagType: TEMPLATE)   → codegenNode: undefined（容器节点，不会生成代码）
```

---

# 四、Phase 2: Transform（转换优化）

## 4.1 核心概念

Transform 阶段不改变模板语义，而是为代码生成做准备：

1. **类型分析**：区分静态/动态内容（PatchFlags）
2. **结构转换**：v-if → 条件表达式、v-for → renderList
3. **表达式转换**：msg → _ctx.msg（prefixIdentifiers）
4. **静态提升**：不变节点提取到 render 外部
5. **Block Tree**：将模板组织为动态节点收集的 Block 结构

## 4.2 两种 Transform

### NodeTransform

```tsx
type NodeTransform = (
  node: RootNode | TemplateChildNode,
  context: TransformContext,
) => void | (() => void) | (() => void)[]
```

- 返回 `void` → 无出口钩子
- 返回函数 → **出口钩子**（子节点处理完后执行）
- 返回函数数组 → 多个出口钩子

### DirectiveTransform

```tsx
type DirectiveTransform = (
  dir: DirectiveNode,
  node: ElementNode,
  context: TransformContext,
) => DirectiveTransformResult
```

按指令名分发（`context.directiveTransforms[name]`）。

## 4.3 Transform 预设序列

```tsx
// compile.ts - getBaseTransformPreset()
[
  // ===== 结构型（改变节点树结构） =====
  transformVBindShorthand,  // v-bind 简写展开（:xxx → v-bind:xxx）
  transformOnce,            // v-once → 缓存标记
  transformIf,              // v-if → IF 条件链节点
  transformMemo,            // v-memo → 缓存依赖数组
  transformFor,             // v-for → FOR 节点（含 source/value/key/index）
  // compat: transformFilter // Vue 2 过滤器兼容

  // ===== 表达式型（非浏览器） =====
  transformExpression,      // msg → _ctx.msg（prefixIdentifiers 模式）
                            // 同时做常量检测和 hoist 注册

  // ===== 元素型 =====
  transformSlotOutlet,      // <slot> → renderSlot() 调用
  transformElement,         // 核心：构建 codegenNode（props/children/directives/patchFlag）
  trackSlotScopes,          // slot 作用域追踪（嵌套 slot 的 scopeId 收集）
  transformText,            // 合并相邻文本+插值为 COMPOUND_EXPRESSION → TEXT_CALL

  // ===== 用户自定义（后执行） =====
  ...options.nodeTransforms
]
```

**执行顺序至关重要**：
- `transformIf/For` 在 `transformElement` **之前**执行。因为 `transformElement` 读取子节点的 `codegenNode`，必须先让结构型 transform 把 v-if/v-for 转换为对应的 JS 节点。
- `transformExpression` 在 `transformElement` **之前**执行。因为 `transformElement` 需要处理已经 prefix 过的表达式来做 patchFlag 推断。
- `transformText` 在 `transformElement` **之后**（因为它在 preset 末尾）。文本合并发生在元素处理之后。

## 4.4 遍历机制

```tsx
// transform.ts
export function traverseNode(
  node: RootNode | TemplateChildNode,
  context: TransformContext,
) {
  // 1. 执行 nodeTransforms（逐个应用）
  const exitFns: (() => void)[] = []
  for (const transform of context.nodeTransforms) {
    const onExit = transform(node, context)
    if (onExit) {
      if (isArray(onExit)) exitFns.push(...onExit)
      else exitFns.push(onExit)
    }
    if (!context.currentNode) return // 节点被移除
  }

  // 2. 递归遍历子节点
  switch (node.type) {
    case NodeTypes.IF_BRANCH:
    case NodeTypes.FOR:
    case NodeTypes.ELEMENT:
    case NodeTypes.ROOT:
      traverseChildren(node, context)
      break
    // Interpolation/Text/Comment 无子节点
  }

  // 3. 逆序执行出口钩子
  context.currentNode = node
  let i = exitFns.length
  while (i--) {
    exitFns[i]()
  }
}
```

**出口钩子逆序执行**的原因：后注册的 transform 往往依赖前面 transform 的处理结果，逆序确保”先入后出”。

## 4.5 静态提升（Hoisting）

```tsx
// transformElement.ts — 出口钩子中
if (isStatic(node) && !isComponent) {
  // 标记为 hoisted
  context.hoist(node.codegenNode!)
  // 创建引用
  node.codegenNode = createSimpleExpression(`_hoisted_${hoistIndex}`, false, ...)
}
```

提升结果存储在 `RootNode.hoists` 数组中，代码生成时作为 preamble 输出：

```jsx
// 生成的代码
const _hoisted_1 = createStaticVNode('<div><span>static</span></div>', 1)
```

### Hoist 分级

```
isStatic(node) 判断：
  → 元素本身静态（无动态绑定）
  → 所有子节点静态
  → 没有 v-for/v-if 结构指令

常量类型升格：
  NOT_CONSTANT → CAN_SKIP_PATCH → CAN_CACHE → CAN_STRINGIFY
```

## 4.6 Block Tree 与 PatchFlags

Vue 3 的编译优化核心：Block Tree。

```
传统 Diff: 遍历整棵树对比
Block Tree: 只追踪"动态节点"

┌──────────────────────────────────────┐
│  Block (openBlock + createBlock)     │
│  ├── 静态节点（跳过）                  │
│  ├── 动态节点 [tracked]  ← patchFlag  │
│  │   ├── 子 Block                     │
│  │   └── 子 Block                     │
│  └── 静态节点（跳过）                  │
└──────────────────────────────────────┘
```

### PatchFlags 位掩码

| Flag | 值 | 含义 |
| --- | --- | --- |
| `TEXT` | 1 | 动态文本 |
| `CLASS` | 2 | 动态 class |
| `STYLE` | 4 | 动态 style |
| `PROPS` | 8 | 动态属性（不含 class/style） |
| `FULL_PROPS` | 16 | 动态 key（需 full diff） |
| `HYDRATE_EVENTS` | 32 | 需要 hydrate 事件 |
| `STABLE_FRAGMENT` | 64 | 子节点顺序稳定 |
| `KEYED_FRAGMENT` | 128 | 有 key 的 fragment |
| `UNKEYED_FRAGMENT` | 256 | 无 key 的 fragment |
| `NEED_PATCH` | 512 | 总是需要 patch |
| `DYNAMIC_SLOTS` | 1024 | 动态 slot |
| `HOISTED` | -1 | 已静态提升（跳过） |
| `BAIL` | -2 | 退出优化（全量 diff） |

### 计算时机

```tsx
// transformElement.ts 出口钩子
// 遍历 props → 累积 patchFlag
if (hasDynamicText) patchFlag |= PatchFlags.TEXT
if (hasDynamicClass) patchFlag |= PatchFlags.CLASS
if (hasDynamicStyle) patchFlag |= PatchFlags.STYLE
if (hasDynamicProps) {
  patchFlag |= PatchFlags.PROPS
  dynamicProps = [...dynamicPropNames].join(',')
}
```

## 4.7 事件缓存（cacheHandlers）

```tsx
// vOn.ts
// 编译选项 cacheHandlers: true →
// onClick: $event => handleClick(arg)  →  onClick: _cache[0] || (_cache[0] = $event => handleClick(arg))
```

避免每次渲染创建新的函数引用，减少子组件的无意义重渲染。

## 4.8 v-model 编译

```
<input v-model="msg" />

编译为:
<input
  modelValue={msg}
  onUpdate:modelValue={$event => (msg = $event)}
/>
```

不同元素有不同的指令编译策略：
- `<input type="text">` → `value` + `@input`
- `<input type="checkbox">` → `checked` + `@change`（数组处理）
- `<select>` → `value` + `@change`
- 组件 → `modelValue` + `onUpdate:modelValue`
- 修饰符（.trim/.number/.lazy）→ 包裹转换逻辑

---

# 五、Phase 3: Codegen（代码生成）

## 5.1 两种模式

### Module 模式（SFC）

```jsx
import { createElementVNode as _createElementVNode, toDisplayString as _toDisplayString, ... } from "vue"

const _hoisted_1 = /*@__PURE__*/_createStaticVNode("<div>static</div>", 1)

export function render(_ctx, _cache) {
  return (_openBlock(), _createElementBlock("div", null, [
    _createElementVNode("span", null, _toDisplayString(_ctx.msg), 1 /* TEXT */)
  ]))
}
```

### Function 模式（浏览器编译）

```jsx
const { createElementVNode: _createElementVNode, ... } = Vue

return function render(_ctx, _cache) {
  return (_openBlock(), _createElementBlock(...))
}
```

## 5.2 Preamble 生成

```
静态提升 → hoists 数组 → 在 render 函数之前生成

const _hoisted_1 = createStaticVNode(...)
const _hoisted_2 = createElementVNode(...)
```

## 5.3 genNode 递归

```tsx
function genNode(node: CodegenNode, context: CodegenContext) {
  switch (node.type) {
    case NodeTypes.ELEMENT:
    case NodeTypes.IF:
    case NodeTypes.FOR:
      genNode(node.codegenNode!, context)  // 已转换，跳转到 codegenNode
      break

    case NodeTypes.TEXT:
      genText(node, context)
      break

    case NodeTypes.VNODE_CALL:
      genVNodeCall(node, context)          // createElementVNode/createBlock
      break

    case NodeTypes.JS_CALL_EXPRESSION:
      genCallExpression(node, context)
      break

    case NodeTypes.JS_CONDITIONAL_EXPRESSION:
      genConditionalExpression(node, context)  // 三元表达式
      break

    // ... 其他 JS AST 节点
  }
}
```

### VNodeCall 生成

```tsx
function genVNodeCall(node: VNodeCall, context: CodegenContext) {
  const { push, helper } = context
  const { tag, props, children, patchFlag, dynamicProps, directives, isBlock, disableTracking } = node

  if (directives) {
    push(helper(WITH_DIRECTIVES) + `(`)
  }
  if (isBlock) {
    push(`(${helper(OPEN_BLOCK)}(${disableTracking ? 'true' : ''}), `)
  }

  const fn = isBlock ? getVNodeBlockHelper(...) : getVNodeHelper(...)
  push(helper(fn) + `(`, NewlineType.None, node)

  // tag, props, children, patchFlag, dynamicProps
  genNodeList(
    genNullableArgs([tag, props, children, patchFlag, dynamicProps]),
    context
  )

  push(`)`)
  if (isBlock) push(`)`)
  if (directives) {
    push(`,${genDirectives(node, context)})`)
  }
}
```

## 5.4 Source Map 生成

```tsx
// codegen.ts
push(code, newlineIndex, node) {
  context.code += code
  if (context.map && node) {
    // 从 node.loc 读取原始位置
    if (node.loc.source) {
      addMapping(node.loc.start, name)
    }
    // 换行时推进位置
    advancePositionWithMutation(context, code)
  }
}

function addMapping(loc: Position, name: string | null) {
  context.map!._mappings.add({
    source: context.filename,
    originalLine: loc.line,
    originalColumn: loc.column - 1,
    generatedLine: context.line,
    generatedColumn: context.column - 1,
    name,
  })
}
```

---

# 六、Template Explorer 验证链

Vue 仓库内置 `packages-private/template-explorer`，用 Monaco Editor 提供实时编译可视化：

```
模板输入（左侧编辑器）
    │
    ▼
compiler-dom.compile() / compiler-ssr.compile()
    │
    ▼
输出 JS 渲染函数 + AST（右侧编辑器 + 控制台）
    │
    ▼
Source Map 双向光标联动（Monaco 装饰器）
```

启动方式：

```bash
# 方式1：本地 Monaco
pnpm dev-compiler     # 构建并启动 template-explorer
pnpm open             # 打开浏览器

# 方式2：CDN Monaco
# 直接访问 template-explorer/local.html（需要先 pnpm dev template-explorer）
```

---

# 七、完整数据流示例

## 输入模板

```html
<div class="container">
  <p>Hello {{ name }}</p>
  <button@click="count++">{{ count }}</button>
</div>
```

## Phase 1: Parse → AST

```
RootNode {
  children: [
    ElementNode {
      tag: "div",
      tagType: ELEMENT,
      props: [AttributeNode { name: "class", value: "container" }],
      children: [
        ElementNode {
          tag: "p",
          children: [
            TextNode { content: "Hello " },
            InterpolationNode { content: SimpleExpression { content: "name" } }
          ]
        },
        ElementNode {
          tag: "button",
          props: [
            DirectiveNode { name: "on", arg: "click", exp: "count++" }
          ],
          children: [
            InterpolationNode { content: SimpleExpression { content: "count" } }
          ]
        }
      ]
    }
  ]
}
```

## Phase 2: Transform → 优化后 AST

```
RootNode {
  hoists: [],  // 无静态提升
  children: [
    ElementNode {
      codegenNode: VNodeCall {
        tag: "div",
        props: { properties: [...] },
        children: [
          VNodeCall {
            tag: "p",
            children: TEXT_CALL {
              codegenNode: CallExpression {
                callee: CREATE_TEXT,
                arguments: [CompoundExpression { children: ["Hello ", _ctx.name] }]
              }
            },
            patchFlag: 1 /* TEXT */
          },
          VNodeCall {
            tag: "button",
            props: { properties: [{ key: "onClick", value: $event => (_ctx.count++) }] },
            children: TEXT_CALL {
              codegenNode: CallExpression {
                callee: TO_DISPLAY_STRING,
                arguments: [_ctx.count]
              }
            },
            patchFlag: 9 /* TEXT + PROPS */
          }
        ],
        patchFlag: 0  // div 本身无动态，但因子节点有动态 → block 追踪
      }
    }
  ]
}
```

## Phase 3: Generate → JavaScript

```jsx
import { createElementVNode as _createElementVNode, createTextVNode as _createTextVNode, toDisplayString as _toDisplayString, openBlock as _openBlock, createElementBlock as _createElementBlock } from "vue"

export function render(_ctx, _cache, $props, $setup, $data, $options) {
  return (_openBlock(), _createElementBlock("div", { class: "container" }, [
    _createElementVNode("p", null, [
      _createTextVNode("Hello " + _toDisplayString(_ctx.name), 1 /* TEXT */)
    ]),
    _createElementVNode("button", {
      onClick: $event => (_ctx.count++)
    }, _toDisplayString(_ctx.count), 9 /* TEXT, PROPS */)
  ]))
}
```

---

# 八、编译时常量 tree-shaking

Vue 3 编译器大量使用编译时常量 `__DEV__` / `__BROWSER__` / `__FEATURE_*__` 控制死代码消除：

```tsx
// 源码中的典型模式
if (__DEV__) {
  warn(`some warning`)
}
if (!__BROWSER__) {
  // Node.js only: 使用 entities/decode 库
  this.entityDecoder = new EntityDecoder(...)
}
```

| 常量 | 什么场景为 true | 控制的代码 |
| --- | --- | --- |
| `__DEV__` | 开发构建 | 警告、校验、devtools 钩子 |
| `__BROWSER__` | esm-browser / global | 排除 Node 专有代码（entities、fs） |
| `__GLOBAL__` | IIFE (全局构建) | 使用 `Vue.xxx` 而非 import |
| `__ESM_BUNDLER__` | tree-shaking 友好 | import 语句保持原样（bundle 工具处理） |
| `__ESM_BROWSER__` | 浏览器原生 ESM | import from URL / 特定浏览器逻辑 |
| `__CJS__` | CommonJS | require() 语法 |
| `__SSR__` | 非 global | SSR 专属渲染路径 |
| `__FEATURE_SUSPENSE__` | v3.5.35 = true | Suspense 功能 |
| `__FEATURE_OPTIONS_API__` | v3.5.35 = true | Options API 支持 |
| `__FEATURE_PROD_DEVTOOLS__` | v3.5.35 = false | 生产环境 devtools 钩子 |
| `__COMPAT__` | vue-compat 构建 | Vue 2 兼容逻辑 |

### Dev Build 的 esbuild 配置

```tsx
// scripts/dev.js
define: {
  __DEV__: prod ? `false` : `true`,
  __BROWSER__: String(format !== 'cjs' && !pkg.buildOptions?.enableNonBrowserBranches),
  __FEATURE_SUSPENSE__: `true`,
  __FEATURE_OPTIONS_API__: `true`,
  __FEATURE_PROD_DEVTOOLS__: `false`,
  // ...
}
```

---

# 九、编译器性能架构总结

## 9.1 性能优化清单

| 层级 | 优化 | 说明 |
| --- | --- | --- |
| Tokenizer | CharCodes 数值比较 | 避免字符串比较，`0x3c` 比 `'<'` 快 |
| Tokenizer | fastForwardTo | RCDATA 中跳过逐字符状态机，直接扫描 |
| Tokenizer | ASCII case-insensitive | `c \| 0x20` 做大小写不敏感（消除分支） |
| Tokenizer | `newlines[]` 二分查找 | 大量换行时 O(log n) 定位行列 |
| Parser | `@babel/parser` | 仅解析表达式，不解析整个模板 |
| Transform | 静态提升 (Hoisting) | 不变 VNode 提升到 render 外部 |
| Transform | Block Tree | 跳过静态节点 diff |
| Transform | PatchFlags | 运行时按需 patch，减少不必要比较 |
| Transform | cacheHandlers | 事件函数缓存，避免子组件重渲染 |
| Transform | `PrefixIdentifiers` | 编译时确定变量来源，避免运行时 `with` |
| Codegen | `/*@__PURE__*/` | 标记纯函数，帮助 bundler tree-shaking |
| 全局 | 编译时常量 `__XX__` | Rollup/esbuild 死代码消除 |
| 全局 | Non-browser 分支排除 | 浏览器构建排除 `entities/decode` 等 Node 依赖 |

## 9.2 构建时 vs 运行时分工

```
编译时（尽可能多做）          运行时（尽可能少做）
─────────────────────      ─────────────────────
静态分析 + 提升              patchFlag 快速路径
PatchFlags 位标记           仅 patch 动态部分
事件缓存                    直接使用缓存引用
常量字符串化                createStaticVNode
Block Tree 结构             dynamicChildren 遍历
prefixIdentifiers           直接访问 _ctx.xxx
```

---

# 十、源码阅读指引

## 核心文件入口

```
packages/compiler-core/src/
├── compile.ts          ⭐ 编译入口 (baseCompile)
├── tokenizer.ts        ⭐ 词法分析状态机
├── parser.ts           ⭐ 语法分析 + AST 构建
├── ast.ts              ⭐ AST 节点类型定义
├── transform.ts        ⭐ Transform 遍历引擎
├── codegen.ts          ⭐ 代码生成
│
├── options.ts              编译选项
├── errors.ts               错误码 + 错误创建
├── runtimeHelpers.ts       运行时 helper 符号
├── utils.ts                工具函数
│
├── transforms/
│   ├── transformElement.ts ⭐⭐ 核心：构建 VNodeCall + patchFlag
│   ├── transformExpression.ts ⭐ prefixIdentifiers + 常量检测
│   ├── transformText.ts    文本合并 + TEXT_CALL
│   ├── vIf.ts              v-if → 条件表达式
│   ├── vFor.ts             v-for → renderList
│   ├── vSlot.ts            v-slot → 插槽函数
│   ├── vModel.ts           v-model → modelValue + onUpdate
│   ├── vOn.ts              v-on / @click → onClick
│   ├── vBind.ts            v-bind → 动态 props
│   ├── vOnce.ts            v-once → CacheExpression
│   ├── vMemo.ts            v-memo → 依赖数组缓存
│   ├── transformSlotOutlet.ts  <slot/> → renderSlot
│   ├── transformVBindShorthand.ts 简写展开
│   ├── cacheStatic.ts      静态缓存
│   └── noopDirectiveTransform.ts 空指令占位
│
├── compat/
│   ├── compatConfig.ts     Vue 2 兼容配置
│   └── transformFilter.ts  Vue 2 过滤器兼容
│
└── __tests__/
```

---

*文档生成时间：2026-08-05 | 源码版本：vuejs/core v3.5.35*