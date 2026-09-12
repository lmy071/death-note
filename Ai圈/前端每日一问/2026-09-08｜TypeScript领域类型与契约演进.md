# 2026-09-08｜TypeScript领域类型与契约演进

## 题目

你负责一个拥有 80+ 前端开发者、20+ 业务域的 Vue 3 Monorepo。系统包含主应用、多个业务包、共享组件库、BFF SDK，以及部分独立部署的微前端。随着项目增长，团队大量复用 TypeScript 类型：一个 `User`、`Order` 或 `PageConfig` 接口经常同时被 API DTO、Pinia Store、Vue 组件 Props、表单模型、缓存结构和跨微前端事件直接引用。

现在出现以下问题：后端字段调整会引发数十个包连锁修改；共享类型包越来越大并形成事实上的“全局 schema”；不同业务域对同一实体的语义并不一致；为了兼容历史数据，大量字段被改成 optional；开发者通过 `as`、非空断言绕过类型错误；微前端独立发布后，新旧版本同时在线时偶发运行时协议不兼容。

请你作为前端架构师，设计一套 **TypeScript 领域类型体系与跨边界契约演进方案**。要求既保持较强的静态类型能力，又不能让 TypeScript 类型依赖破坏业务域自治和独立发布能力。请说明类型应该如何分层、哪些边界必须做 Runtime Validation、如何进行版本演进，以及如何通过工程化手段防止类型系统逐渐退化。

## 背景 / 场景

当前代码中存在典型写法：后端 OpenAPI 生成的 `OrderDTO` 被直接放入 Pinia，并继续作为多个 Vue 组件的 Props；微前端之间通过 Event Bus 传递同一个共享 npm 包里的 `Order` 类型。编译期所有应用都能通过，但当 Host 为 N+1、Remote 仍为 N 版本时，事件新增字段或改变枚举值后出现运行时异常。

业务希望继续支持各团队独立发布，因此不能简单要求“所有项目锁定同一个 shared-types 版本并同时上线”。同时，架构治理不能完全依赖 Code Review，需要能够在 CI 和运行时发现契约破坏。

## 核心考察点

- **类型边界设计**：能否区分 Transport DTO、Domain Model、View Model、Form Model、Persistence Model，而不是建立一个万能 `User` / `Order` 接口。
- **静态类型与运行时事实的边界**：理解 TypeScript 类型擦除，知道网络响应、localStorage / IndexedDB、postMessage、Event Bus、微前端输入、AI/第三方数据等不可信边界不能只依赖静态类型。
- **Anti-Corruption Layer**：API DTO 进入业务域后通过 Mapper / Adapter 转换为领域模型，避免后端 schema 直接污染 Vue 组件和状态层。
- **契约演进**：Additive Change、Breaking Change、Expand / Contract、版本协商、旧消费者兼容窗口以及 Producer/Consumer 独立部署。
- **Runtime Validation**：在系统边界使用 Schema Validator，将 `unknown` 解析为可信领域类型，并设计失败策略与遥测。
- **类型所有权**：类型应由业务域或协议所有者维护，而不是所有团队依赖一个无限增长的 `shared-types` 包。
- **Type-level Architecture Tests**：通过依赖规则、API Extractor / 类型快照、契约测试和 CI 检查阻止非法跨层引用。
- **Vue 3 架构结合**：Store 保存领域状态而非 Transport DTO；组件 Props 尽量面向稳定 View Model / Capability，而不是整个后端实体。

## 追问方向

1. 为什么 `interface Order { ... }` 在 TypeScript 编译通过，不能证明从 API 收到的对象真的满足 `Order`？如果 Runtime Validation 全量执行会带来性能成本，你如何选择验证边界？
2. 一个后端枚举从 `pending | paid` 增加 `refunding`，为什么从服务端视角可能是 additive change，但对前端仍可能是 breaking change？如何设计客户端避免这种问题？
3. 微前端 A 发布新版事件 `order.updated.v2`，Host 和其他 Remote 仍可能运行旧版本。你会采用事件版本号、Capability Negotiation、Schema Registry，还是其他方案？分别有什么成本？
4. 是否应该让所有业务包依赖统一的 `@company/shared-types`？如果不应该，真正适合进入共享包的类型是什么？
5. 如果一个 `OrderDTO` 有 80 个字段，而某组件只需要 `id`、`status`、`amount`，Props 应该直接使用 `OrderDTO`、`Pick<OrderDTO, ...>`，还是定义独立 View Model？说明长期演进差异。
6. 如何检测代码库中 `any`、双重断言 `as unknown as X`、非空断言和超大 optional interface 的扩散，并区分合理逃生舱与架构腐化？
7. OpenAPI / GraphQL 自动生成类型应该位于架构哪一层？生成代码是否应该被业务代码直接依赖？
8. 当 IndexedDB 中保存的是 v3 数据，而新版本应用 Domain Model 已升级到 v6，你如何设计 Schema Migration，使类型定义、数据迁移和失败恢复保持一致？

## 参考答案要点

### 1. 不建立“全局实体类型”，按边界建立类型

推荐至少区分：

`Transport DTO → Boundary Parser → Domain Model → Selector / Mapper → View Model`

表单、持久化和跨应用协议根据生命周期再拥有独立模型。关键不是类型数量越少越好，而是让变化被限制在正确的边界内。

例如后端将 `user_name` 改为 `display_name` 时，理想情况下只影响 generated DTO、Runtime Schema 和 DTO → Domain Mapper，而不应该导致几十个 Vue 组件一起修改。

### 2. 外部数据首先是 unknown，而不是“相信泛型”

`fetch<OrderDTO>()` 或 `axios.get<OrderDTO>()` 只是在编译期告诉 TypeScript 开发者希望它是什么，并没有验证响应体。

对于高风险边界应执行 Runtime Validation：API 响应、跨 iframe / Worker / 微前端消息、本地持久化恢复、Feature Config、第三方 SDK 数据等。解析成功后才能进入 trusted domain。验证失败应产生结构化错误，而不是静默使用半合法对象。

不必在每个内部函数重复验证。应把 validation 集中在 trust boundary，使内部领域代码可以依赖已经建立的 invariant。

### 3. Domain Model 应表达业务不变量

不要因为 API 某字段偶尔缺失，就把整个领域模型逐渐变成：

```tsx
interface Order {
  id?: string
  status?: string
  amount?: number
}
```

这会把边界的不确定性传播到整个系统。Boundary Parser / Mapper 应负责处理缺失、默认值、旧版本兼容或拒绝非法数据，使领域层获得更强 invariant。

对 ID、Money、状态机等关键语义，可以使用 branded / opaque type、discriminated union 和 exhaustive checking 提高表达能力。

### 4. API Generated Types 是基础设施类型，不等于领域类型

OpenAPI / GraphQL 生成代码应位于 infrastructure / transport 层。业务域通过 Repository 或 Client Adapter 消费它，再映射到自己的 Domain Model。

如果 Vue 页面、Store 和组件普遍 import generated DTO，意味着 API schema 已经穿透整个前端架构，后端一次结构调整就会形成高 fan-out change。

### 5. 跨独立部署单元要设计协议，而不是共享 TypeScript 接口

微前端之间即使 import 同一个 interface，也无法保证运行时双方加载的是同一版本。因此跨应用通信应视为分布式系统协议。

事件建议具备稳定 envelope，例如 `eventId`、`eventType`、`schemaVersion`、`producerVersion`、`timestamp`、`payload`。消费者对自己支持的 schema 进行解析；未知版本应降级、忽略或进入兼容 Adapter，而不是直接强制断言。

关键事件可以建立 Consumer-driven Contract Test，CI 验证 Producer 的新 schema 是否仍满足活跃消费者契约。

### 6. 版本演进优先 Additive + Expand / Contract

先让消费者能够处理新旧结构，再让 Producer 开始发送新结构；等待兼容窗口结束后再删除旧字段。Breaking Change 必须显式升级协议版本。

枚举扩展尤其需要注意。客户端如果写出穷举后直接假定“永远只有两个值”，服务端新增枚举虽然没有删除字段，仍可能让旧客户端进入非法状态。可以在 Boundary 层把未知服务端值映射为 `unknown` / `unsupported`，并上报 telemetry。

### 7. Vue 3 Store 与组件面向领域和 UI 能力

Pinia 不应成为 API DTO 缓存桶。Store 应保存业务真正需要的 Domain State；API 数据通过 Repository / Mapper 进入 Store。

组件 Props 也不应因为方便就接受巨型 `OrderDTO`。长期稳定的公共组件更适合接受最小 Capability / View Model，例如 `OrderSummaryViewModel`。相比 `Pick<OrderDTO, ...>`，独立 View Model 可以解除命名、optional 语义以及 transport schema 与 UI contract 的隐式绑定。

### 8. 用工程规则保护架构，而不是只写规范文档

在 Monorepo 中建立 dependency constraints，例如：`presentation` 不能直接 import `infrastructure/generated-api`；跨 domain 只能依赖对方公开的 application contract；禁止 deep import。

CI 可以加入：public API / `.d.ts` diff、Breaking Change 检测、Contract Test、Schema compatibility check、循环依赖检测，以及 `any` / unsafe assertion budget。对于确实需要逃生的 unsafe cast，要求局部封装并留下原因，而不是全面禁止后逼迫开发者换一种写法绕过规则。

### 9. 可观测性覆盖“契约错误”

Runtime Validation Failure 应记录 `schemaVersion`、producer、consumer、applicationVersion、字段路径和错误类型，但避免上传敏感 payload。

监控指标可以包括 validation failure rate、unknown enum rate、migration failure rate、contract fallback rate。发布平台应能够关联某个 Producer 版本上线后哪些旧 Consumer 开始出现解析失败，从而快速判断兼容性事故。

### 10. 最终架构原则

**TypeScript 的价值不是让整个公司共享同一个巨大 interface，而是在每个架构边界建立明确契约。**

静态类型负责可信边界内部的开发期正确性；Runtime Schema 负责跨信任边界的数据真实性；Mapper / ACL 负责隔离变化；版本化协议和契约测试负责独立部署场景下的时间维度兼容性。真正成熟的类型体系，应降低变化的传播半径，而不是让一次 schema 修改产生更大规模的“类型安全连锁编译失败”。