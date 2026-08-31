# PageAgent — AI 操作页面逻辑

# PageAgent — AI 操作页面逻辑

PageAgent 是由阿里巴巴开源的一个纯客户端 JavaScript GUI Agent，它的核心思想是：**让 AI 直接在你的网页里操作界面**，不需要浏览器插件、Python 脚本、无头浏览器或截图。

> 仓库地址：[https://github.com/alibaba/page-agent](https://github.com/alibaba/page-agent)
> 

---

## 一、核心理念

一句话概括：**把 GUI Agent 搬进浏览器页面里**。

传统的 AI 操作页面的方式（比如 browser-use）依赖：

- 无头浏览器（headless Chrome）
- 截图 → 多模态模型分析 → 生成操作指令
- 需要额外的浏览器插件或 Python 运行环境

PageAgent 换了一个思路：

- 直接在**页面内**注入 JavaScript
- 通过 **DOM 文本化**（把 DOM 树序列化成文本描述）让 LLM 理解页面结构
- LLM 生成操作指令后，直接在页面内执行对应的 DOM 操作
- **不需要截图、不需要多模态模型**，普通文本 LLM 就能驱动

---

## 二、AI 操作页面的核心逻辑

### 2.1 整体流程

```
用户输入自然语言指令
        ↓
  [1] DOM 提取 & 序列化
        ↓
  [2] 构造 Prompt（包含 DOM 结构 + 用户指令 + 可用操作）
        ↓
  [3] 发送给 LLM（任何兼容 OpenAI API 的模型）
        ↓
  [4] LLM 返回操作指令（JSON 格式的 Action）
        ↓
  [5] Action 解析 & 页面执行（点击、输入、滚动等）
        ↓
  [6] 等待页面响应 / 进入下一轮
```

### 2.2 DOM 序列化——AI 如何"看见"页面

PageAgent 不会给 LLM 传入截图的像素数据，而是传入**结构化的文本描述**：

```jsx
// DOM 被序列化成类似这样的文本
[1] <button id="login-btn" class="primary"> 登录 </button>
[2] <input type="text" name="username" placeholder="请输入用户名" />
[3] <input type="password" name="password" placeholder="请输入密码" />
[4] <a href="/forgot"> 忘记密码？</a>
```

LLM 根据这个结构化的文本描述，就能推理出"应该点击按钮 #1"或"在输入框 #2 输入用户名"。

### 2.3 Action 机制——AI 如何"操作"页面

LLM 返回的操作指令是一个结构化的 JSON Action，支持的操作类型包括：

| Action 类型 | 描述 | 示例 |
| --- | --- | --- |
| `click` | 点击元素 | `click [1]` 点击登录按钮 |
| `input` | 输入文本 | `input [2] "admin"` 在用户名字段填入 |
| `scroll` | 滚动页面 | `scroll down 300` |
| `navigate` | 页面跳转 | `navigate /dashboard` |
| `extract` | 提取数据 | `extract 所有文章标题` |
| `wait` | 等待条件 | `wait for selector ".loaded"` |
| `done` | 任务完成 | `done "登录成功"` |

### 2.4 多轮对话循环

PageAgent 采用 **Plan → Execute → Observe → Re-plan** 的循环模式：

```
┌─────────────────────────┐
│  LLM 生成执行计划       │ ← 根据当前页面状态 + 用户目标
└──────────┬──────────────┘
           ↓
┌─────────────────────────┐
│  执行 Action（click 等）│ ← 在页面中执行
└──────────┬──────────────┘
           ↓
┌─────────────────────────┐
│  观察页面变化            │ ← 重新提取 DOM 文本
└──────────┬──────────────┘
           ↓
    ┌──────┴──────┐
    │ 任务完成？    │
    └──是──┬───否──┘
       结束   回到 Plan
```

这个循环保证了 AI 可以**实时感知页面反馈**，在执行多步操作（如填写表单 → 点击下一步 → 选择下拉菜单）时保持准确的上下文。

---

## 三、技术架构

### 3.1 层级结构

```
┌──────────────────────────────────┐
│         用户自然语言指令           │
└──────────────┬───────────────────┘
               ↓
┌──────────────────────────────────┐
│      PageAgent (JavaScript)       │
│  ┌─────────┐  ┌──────────────┐   │
│  │ DOM Parser│  │ Action Engine│   │
│  └────┬────┘  └──────┬───────┘   │
│       ↓              ↓            │
│  ┌─────────┐  ┌──────────────┐   │
│  │ LLM Conn.│  │ DOM Execution│   │
│  └────┬────┘  └──────────────┘   │
└───────┼──────────────────────────┘
        ↓
┌──────────────────────────────────┐
│      LLM API (任意兼容模型)        │
│  千问 / DeepSeek / GPT / Claude   │
└──────────────────────────────────┘
```

### 3.2 关键设计决策

1. **纯 JavaScript 实现**：不需要后端服务，CDN 引入即可运行
2. **DOM 文本化代替截图**：降低 LLM 成本，普通文本模型即可
3. **Bring Your Own LLM**：不绑定特定模型，使用标准 OpenAI 兼容 API
4. **最小权限**：只在当前页面内操作，不会越权访问其他标签页（除非使用 Chrome 插件）

---

## 四、集成方式

### 4.1 CDN 快速体验

```html
<!-- 页面中引入即可体验 -->
<script src="https://cdn.jsdelivr.net/npm/page-agent@1.8.2/dist/iife/page-agent.demo.js" crossorigin="true"></script>
```

### 4.2 npm 编程集成

```bash
npm install page-agent
```

```jsx
import { PageAgent } from 'page-agent'

const agent = new PageAgent({
  model: 'qwen3.5-plus',                              // 模型名称
  baseURL: 'https://dashscope.aliyuncs.com/compatible-mode/v1',  // LLM API 地址
  apiKey: 'YOUR_API_KEY',
  language: 'zh-CN',                                  // 界面语言
})

// 用自然语言下达指令
await agent.execute('点击登录按钮，输入用户名 admin，密码 123456，然后点击登录')
```

### 4.3 配置选项

```jsx
const agent = new PageAgent({
  model: 'deepseek-chat',
  baseURL: 'https://api.deepseek.com/v1',
  apiKey: 'sk-xxx',
  language: 'zh-CN',
  maxSteps: 10,           // 最大操作步骤数
  planFirst: true,        // 是否先规划再执行
  debug: false,           // 调试模式
  onStep: (step) => {     // 每一步的回调
    console.log(`Step ${step.index}: ${step.action}`)
  }
})
```

---

## 五、核心应用场景

### 5.1 SaaS AI Copilot

在现有的 Web 产品中嵌入 AI 助手，用户用自然语言操作界面，无需重新开发后端逻辑：

- ERP 系统：说"帮我生成上月销售报表" → AI 自动点击菜单、选择筛选条件、导出
- CRM 系统：说"把张三的状态改成已签约，发送确认邮件" → AI 完成多步操作

### 5.2 智能表单填写

将复杂的多步骤表单填写简化为一句自然语言：

- 20 步点击变成一句话
- 适合管理后台、审批系统等场景

### 5.3 无障碍增强

让任何网页都能通过自然语言/语音操作：

- 屏幕阅读器增强
- 语音指令控制页面
- 降低使用门槛

### 5.4 跨页面 Agent（需 Chrome 扩展）

通过可选的 Chrome 扩展，Agent 可以跨越多个标签页执行任务：

- "在 A 页面查询数据，复制到 B 页面的表单中"

### 5.5 MCP Server（Beta）

对外暴露 MCP 接口，让其他 AI Agent 客户端控制你的浏览器。

---

## 六、与同类方案的对比

| 维度 | PageAgent | browser-use | Playwright + AI |
| --- | --- | --- | --- |
| 运行环境 | 纯浏览器端 JS | Python + headless Chrome | Python/Node + 浏览器驱动 |
| 感知方式 | DOM 文本化 | 截图 + 多模态模型 | 截图/DOM |
| 部署复杂度 | 一行 script 标签 | 需要 Python 环境 | 需要安装浏览器驱动 |
| LLM 要求 | 普通文本模型 | 需要多模态（视觉） | 取决于实现 |
| 跨页面 | Chrome 插件可选 | 原生支持 | 原生支持 |
| 适用场景 | 客户端增强、SaaS 集成 | 自动化测试、爬虫 | 自动化测试 |

---

## 七、底层原理深入

### 7.1 DOM 提取算法

PageAgent 使用了类似 browser-use 的 DOM 处理逻辑（该项目基于 browser-use 构建），核心步骤：

1. **遍历 DOM 树**：递归遍历当前页面的 DOM 结构
2. **提取可交互元素**：识别 button、input、select、a、textarea 等可交互元素
3. **生成唯一 ID**：为每个可交互元素分配一个数字索引
4. **提取关键属性**：标签类型、文本内容、placeholder、aria-label、class/id
5. **文本序列化**：将结构化数据压缩成紧凑的文本格式

### 7.2 Prompt 构造

发送给 LLM 的 Prompt 包含三部分：

1. **系统指令**：定义 Agent 的角色、可用操作列表、输出格式
2. **当前页面快照**：DOM 的文本序列化结果
3. **用户目标**：用户输入的自然语言指令

### 7.3 安全保障

- **沙箱限制**：Agent 只在当前页面内操作
- **敏感操作确认**：涉及删除、支付等操作可配置需要用户确认
- **操作追溯**：每一步操作都有日志记录

---

## 八、总结

PageAgent 重新定义了 AI 操作页面的方式——它不是在外部用截图驱动浏览器，而是**住进你的网页里**，通过文本化的 DOM 让 LLM 理解页面，用 JavaScript 直接操作 DOM 完成指令。

核心优势：

- 🎯 **零依赖**：纯 JS，一行 CDN 引入
- 🧠 **低成本**：普通文本 LLM 即可，不需要多模态模型
- 🔧 **可定制**：自备 LLM，使用标准 API
- 🚀 **轻量化**：不依赖浏览器驱动或 Python 环境

这使得 PageAgent 特别适合作为 SaaS 产品的 AI Copilot 嵌入方案——不需要改造后端，直接在页面层叠加 AI 操作能力。

---

*本文内容基于 [PageAgent GitHub 仓库](https://github.com/alibaba/page-agent) 及官方文档整理。*