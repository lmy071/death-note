# 2026-09-10｜AI Tool Calling权限与事务治理

## 题目

你正在设计一个基于 **Vue 3 + LLM/AI Agent** 的企业级工作台。模型可以通过 Tool Calling 调用 50+ 个业务工具，例如查询订单、修改配置、创建工单、发送消息、发起退款等。

目前系统存在几个问题：模型可能重复调用工具；用户取消生成后，后端工具仍继续执行；多个 Tool Call 并发时可能发生业务状态竞争；高风险操作仅靠 Prompt 约束；前端刷新后无法准确恢复哪些操作已经执行；模型重试可能导致同一个退款操作执行两次。

请从前端架构师视角设计一套 **Tool Calling 执行协议、权限模型、状态机与故障恢复体系**。要求既支持流式 AI 交互，又能保证高风险业务操作的安全性、幂等性、可审计性和可恢复性。

## 背景 / 场景

系统链路如下：

`Vue 3 Client → AI Gateway → Agent Runtime → Tool Gateway → Business Services`

一个 Agent Run 可能持续数分钟，并产生多个 Tool Call。Tool 分为只读、低风险写、高风险写三类。部分操作需要用户确认；部分工具执行后不可撤销。网络可能断开，浏览器可能刷新，模型和 Agent Runtime 都可能重试。

要求前端能够准确展示每个 Tool Call 的生命周期，并避免把“模型说已经执行”和“业务系统真正提交成功”混为一谈。

## 核心考察点

- **Tool Call 与业务执行解耦**：模型只能产生 Tool Intent，不应直接拥有业务系统执行权限。
- **Capability / Policy 模型**：按用户、会话、Agent、Tool、参数范围和风险等级计算实际权限，而不是依赖 Prompt。
- **Tool Call 状态机**：至少区分 `proposed → validating → awaiting_approval → executing → committed / failed / cancelled / unknown`。
- **幂等性设计**：使用 `runId + toolCallId + idempotencyKey`，避免 Agent Retry、网络 Retry 或用户重复点击导致副作用重复执行。
- **事务边界**：理解浏览器、Agent Runtime 和业务服务之间无法依赖单一 ACID 事务，需要 Saga / Compensation 或业务级幂等协议。
- **Human-in-the-loop**：高风险 Tool 必须由可信 Policy Engine 决定是否进入审批，而不是由模型自行判断。
- **Cancellation 语义**：区分取消 AI Run、取消等待中的 Tool、尝试取消正在执行的 Tool，以及不可撤销的已提交操作。
- **状态恢复**：刷新或断线后通过服务端 Event Log / Snapshot 恢复真实执行状态，而不是只恢复前端 Pinia 内存状态。
- **并发控制**：处理多个 Tool Call 修改同一资源时的 optimistic concurrency、version / ETag 或资源锁策略。
- **可观测性与审计**：建立 `traceId → runId → toolCallId → businessOperationId` 的链路关联。

## 追问方向

1. SSE 已经告诉前端 `tool.completed`，但业务服务实际响应超时，你会如何定义 `completed`？
2. 用户点击“确认退款”后浏览器立即断网，再次进入页面时如何判断退款到底有没有发生？
3. Agent 因模型超时重新规划并再次产生语义相同的 Tool Call，如何避免重复副作用？
4. 用户点击“停止生成”是否应该自动取消所有 Tool Call？为什么？
5. Tool A 成功、Tool B 失败，而 Tool B 依赖 Tool A，你如何处理补偿？
6. 如果 Tool 参数来自 RAG 检索到的恶意文档，Prompt Injection 如何跨越模型层影响 Tool 执行？
7. Vue 3 前端应该保存 Tool 的权威状态，还是只保存服务端状态的 projection？
8. 如何设计 Tool Schema 的版本升级，使旧客户端和运行中的 Agent Run 不被破坏？

## 参考答案要点

### 1. 建立 Tool Intent 与 Tool Execution 两层模型

LLM 输出的 Tool Call 本质上只是**执行意图**。Agent Runtime 不应拿模型输出直接调用业务 API，而应先进入 Tool Gateway。

Tool Gateway 负责 Schema Validation、身份解析、Capability 检查、风险分类、参数约束、审批策略、幂等控制和审计记录。这样模型即使被 Prompt Injection 操纵，也不能绕过可信执行边界。

### 2. 使用服务端权威 Tool 状态机

前端不应把 Tool Call 简化为 `loading / success / error`。

推荐状态类似：

```
proposed
  ↓
validating
  ↓
awaiting_approval
  ↓
executing
  ↓
committed
```

并存在 `rejected`、`failed`、`cancelled`、`unknown` 等终态或异常态。

其中 `committed` 应表示**业务系统已经确认副作用提交成功**，而不是 LLM 输出完成，也不是 HTTP 请求已经发出。

### 3. 幂等必须下沉到执行边界

前端按钮禁用无法解决重复执行问题。真正的幂等需要由 Tool Gateway / Business Service 根据稳定的 Idempotency Key 保证。

例如：

```
idempotencyKey = hash(runId + logicalOperationId + normalizedArguments)
```

重复请求应返回第一次业务操作的结果，而不是重新执行副作用。

### 4. 前端是状态 Projection，不是事实来源

Vue 3 可以使用 Pinia 保存 Tool Projection，但权威状态应存在服务端 Event Log / Operation Store。

页面恢复时：

```
GET Run Snapshot
        ↓
Replay missing events
        ↓
Rebuild Tool Projection
        ↓
Resume SSE
```

事件需要 `eventId / sequence / runId / toolCallId / version`，客户端 reducer 应具有幂等性并能处理重复事件。

### 5. Cancellation 不是 AbortController 就结束了

`AbortController.abort()` 只能表达客户端不再等待，并不能证明业务副作用被取消。

需要区分：

- `cancel_requested`：客户端提出取消。
- `cancelled`：执行系统确认没有产生副作用。
- `committed`：取消到达前业务操作已经提交。
- `unknown`：当前无法确认结果，需要 reconciliation。

对于支付、退款等不可安全取消的操作，应查询最终业务状态，而不是向 UI 返回一个虚假的 cancelled。

### 6. 高风险操作采用 Policy + Approval

Tool Metadata 应声明风险能力，例如 `read`、`write`、`financial`、`external_communication`、`destructive`。

Policy Engine 根据用户身份、租户策略、Tool 类型、参数范围和当前上下文决定 `allow / deny / require_approval`。

审批 UI 必须显示经过服务端规范化后的最终参数，例如退款金额、订单号和收款对象，防止用户确认的内容与真正执行的参数发生 TOCTOU 偏差。审批后应绑定参数摘要，任何参数变化都必须重新审批。

### 7. 并发与事务使用业务协议解决

跨 Tool 不应幻想存在一个覆盖浏览器、Agent Runtime 和多个微服务的全局事务。

对可补偿操作可以采用 Saga；对不可补偿操作，需要明确 commit point。资源竞争可以通过业务版本号、ETag、optimistic concurrency control 或必要的服务端锁解决。

Agent 在发生冲突后应该重新读取业务状态再规划，而不是无限 Retry 原请求。

### 8. 建立端到端审计链

至少记录：

```
traceId
runId
modelRequestId
toolCallId
idempotencyKey
approvalId
businessOperationId
actor
policyDecision
argumentsHash
resultStatus
```

这样才能回答“模型为什么调用这个工具、谁批准了、真正执行了什么、业务系统最终发生了什么”。

## 架构师级判断标准

优秀答案不会把问题停留在 `SSE + Pinia + AbortController`。关键是识别出 **LLM 是非确定性的意图生成器，而 Tool Execution 是确定性的受控业务执行系统**。

前端负责交互、审批和状态投影；Agent Runtime 负责编排；Policy / Tool Gateway 建立安全执行边界；业务服务负责最终幂等与事务语义。只有明确这些边界，AI Agent 才能安全地从“回答问题”升级到“执行真实业务操作”。