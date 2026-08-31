# Vue 3 工程化与数组响应式深度解析

> 基于 `vuejs/core` 仓库（v3.5.35，pnpm monorepo）源码分析。
> 
> 
> 涵盖：提交 Hook 体系 → Changelog 生成机制 → 数组响应式演进
> 

---

# 一、提交 Hook 体系

## 1.1 整体架构

```
git commit
    │
    ├── pre-commit hook
    │   ├── pnpm lint-staged  ← 暂存区文件的 linter/formatter
    │   └── pnpm check        ← 全局 TypeScript 类型检查
    │
    └── commit-msg hook
        └── node scripts/verify-commit.js  ← message 格式校验
```

## 1.2 Hook 注册机制

Vue 3 使用 `simple-git-hooks`（而非 Husky）管理 Git hooks，并通过 `postinstall` 在安装依赖后同步 hook 配置：

```json
// package.json
{
  "scripts": {
    "postinstall": "simple-git-hooks"
  },
  "simple-git-hooks": {
    "pre-commit": "pnpm lint-staged && pnpm check",
    "commit-msg": "node scripts/verify-commit.js"
  }
}
```

`postinstall` 在每次 `pnpm install` 后自动执行 `simple-git-hooks`，将配置同步到 `.git/hooks/` 目录。

### Shell 模板

两个 hook 共用同一模板，通过环境变量支持跳过：

```bash
#!/bin/sh
if [ "$SKIP_SIMPLE_GIT_HOOKS" = "1" ]; then
    echo "[INFO] SKIP_SIMPLE_GIT_HOOKS is set to 1, skipping hook."
    exit 0
fi
if [ -f "$SIMPLE_GIT_HOOKS_RC" ]; then
    . "$SIMPLE_GIT_HOOKS_RC"
fi

# pre-commit 执行：
pnpm lint-staged && pnpm check

# commit-msg 执行：
node scripts/verify-commit.js
```

---

## 1.3 Hook 一：pre-commit

### 流程

```
pre-commit 触发
    │
    ├── SKIP_SIMPLE_GIT_HOOKS=1 → exit 0（跳过）
    │
    ├── pnpm lint-staged（仅暂存区文件）
    │   ├── *.js  *.json → prettier --write
    │   └── *.ts  *.tsx  → eslint --fix → prettier --write
    │
    └── pnpm check
        └── tsc --incremental --noEmit（全量类型检查）
```

### Step 1：lint-staged

```json
{
  "lint-staged": {
    "*.{js,json}": ["prettier --write"],
    "*.ts?(x)": [
      "eslint --fix",
      "prettier --parser=typescript --write"
    ]
  }
}
```

| 文件类型 | 第一道 | 第二道 |
| --- | --- | --- |
| `*.js` `*.json` | — | `prettier --write` |
| `*.ts` `*.tsx` | `eslint --fix`（逻辑修复） | `prettier --write`（格式统一） |

### Step 2：pnpm check

```json
{ "scripts": { "check": "tsc --incremental --noEmit" } }
```

- `--incremental` — 复用 `.tsbuildinfo` 中的上次编译状态，减少重复检查工作
- `--noEmit` — 仅做类型检查，不产出 JS
- 检查范围由根 `tsconfig.json` 的 `include` 决定，不只限于暂存文件

> CI 的 `lint-and-test-dts` job 同样执行 `pnpm run check`，随后再执行 `pnpm run test-dts`；并非使用 `vue-tsc -b`。
> 

### 跳过方式

```bash
# 仅跳过 pre-commit（也会跳过 commit-msg）
SKIP_SIMPLE_GIT_HOOKS=1 git commit -m "..."

# 跳过所有 hooks
git commit --no-verify -m "..."
```

---

## 1.4 Hook 二：commit-msg

### 校验脚本源码

```jsx
// scripts/verify-commit.js
import pico from 'picocolors'
import { readFileSync } from 'node:fs'
import path from 'node:path'

const msgPath = path.resolve('.git/COMMIT_EDITMSG')
const msg = readFileSync(msgPath, 'utf-8').trim()

const commitRE =
  /^(revert: )?(feat|fix|docs|dx|style|refactor|perf|test|workflow|build|ci|chore|types|wip|release)(\(.+\))?: .{1,50}/

if (!commitRE.test(msg)) {
  // 打印红色错误信息
  console.error(
    `  ERROR  invalid commit message format.\n\n` +
    `  Proper commit message format is required for automated changelog generation.\n\n` +
    `    feat(compiler): add 'comments' option\n` +
    `    fix(v-model): handle events on blur (close #28)\n\n` +
    `  See .github/commit-convention.md for more details.\n`
  )
  process.exit(1)  // 非零退出 → git 拒绝提交
}
```

### 正则拆解

```
^(revert: )?(feat|fix|docs|dx|style|refactor|perf|test|workflow|build|ci|chore|types|wip|release)(\(.+\))?: .{1,50}
```

| 分组 | 正则 | 含义 | 必填 |
| --- | --- | --- | --- |
| revert 前缀 | `(revert: )?` | 回滚提交 | ❌ |
| type | `(feat\|fix\|docs\|...)` | 15 种类型（含 `release`） | ✅ |
| scope | `(\(.+\))?` | 影响范围，如 `(compiler)` | ❌ |
| 分隔符 | `:` | 冒号 + 空格 | ✅ |
| subject | `.{1,50}`（正则末尾没有 `$`） | 至少 1 个字符；当前实现只匹配前 50 个字符，并未强制最大长度 | ✅ |

### 15 种 Type

| Type | 用途 | 进入 Changelog？ | 常见 SemVer 含义（本仓库不据此自动选版本） |
| --- | --- | --- | --- |
| `feat` | 新功能 | ✅ | minor |
| `fix` | Bug 修复 | ✅ | patch |
| `perf` | 性能优化 | ✅ | patch |
| `docs` | 仅文档变更 | ❌ | — |
| `dx` | 开发者体验改进 | ❌ | — |
| `style` | 代码风格（不影响逻辑） | ❌ | — |
| `refactor` | 重构 | ❌ | — |
| `test` | 测试 | ❌ | — |
| `workflow` | 工作流变更 | ❌ | — |
| `build` | 构建系统/外部依赖 | ❌ | — |
| `ci` | CI/CD 配置 | ❌ | — |
| `chore` | 杂项 | ❌ | — |
| `types` | 仅类型定义变更 | ❌ | — |
| `wip` | 进行中 | ❌ | — |
| `release` | 发布提交 | — | — |

> 注意：`verify-commit.js` 的正则没有以 `$` 收尾，因此 `.{1,50}` 不是严格的“最多 50 字符”校验；它只要求冒号后至少存在内容。
> 

> 另：此仓库的目标版本由发布者交互选择或显式传参，`feat` / `fix` / `perf` 不会自动决定 `minor` / `patch`。
> 

### Message 三段式格式（改编自 Angular Convention）

```
<type>(<scope>): <subject>    ← 首行 header（必填；规范建议简洁，当前脚本未强制总长度上限）
                               ← 空行
<body>                         ← 正文 body（可选，解释为什么、怎么做）
                               ← 空行
<footer>                       ← 页脚 footer（可选，BREAKING CHANGE + 关闭 Issue）
```

### 通过 vs 不通过

```bash
# ✅ 通过
feat(compiler): add 'comments' option
fix(v-model): handle events on blur
docs: update contributing guide

# ❌ 不通过
Update code                    # 没有 type
feat:add comments              # 缺少空格
feat(compiler) add comments    # 缺少冒号
FEAT(compiler): add comments   # type 必须全小写
Feature(compiler): add x       # 不在 14 种 type 中
```

---

## 1.5 完整提交流程

```
$ git commit -m "feat(compiler): add 'comments' option"
    │
    ├── 1. pre-commit hook
    │   ├── lint-staged 扫描暂存区
    │   │   ├── *.ts → eslint --fix（逻辑修复）
    │   │   ├── *.ts → prettier --write（格式统一）
    │   │   └── 文件被修改 → 自动 git add 更新暂存区
    │   ├── tsc --incremental --noEmit
    │   │   ├── 读取 .tsbuildinfo 增量缓存
    │   │   ├── 全量类型检查所有 packages
    │   │   └── ❌ 类型错误 → exit 1，提交中断
    │   └── ✅ 通过
    │
    ├── 2. commit-msg hook
    │   ├── 读取 .git/COMMIT_EDITMSG
    │   ├── 正则匹配 type/scope/subject
    │   └── ❌ 不匹配 → 打印红色错误 + 正确示例，exit 1
    │
    ├── 3. git 创建 commit 对象
    └── 🎉 提交成功
```

---

## 1.6 工具选型对比

| 工具 | Vue 3 选型 | 替代方案 | 选择理由 |
| --- | --- | --- | --- |
| Git Hook 管理 | `simple-git-hooks` | Husky | 配置集中在 `package.json`，由 `postinstall` 同步到 `.git/hooks/` |
| 暂存区 lint | `lint-staged` | — | 行业标准 |
| 格式化 | `prettier` | dprint | 生态最大 |
| 代码质量 | `eslint` | biome | Vue 插件成熟 |
| 类型检查 | `tsc --incremental --noEmit` | — | 非构建模式，最快反馈 |
| Commit 校验 | 自制 `verify-commit.js` | commitlint | 零外部依赖（仅 `picocolors`） |
| 终端颜色 | `picocolors` | chalk | 轻量、API 简洁 |

---

# 二、Changelog 生成机制

## 2.1 目录结构

```
vue3/
├── CHANGELOG.md              ← 当前主版本（3.5.x）
├── changelogs/
│   ├── CHANGELOG-3.0.md      ← 3.0.x 归档（11 releases）
│   ├── CHANGELOG-3.1.md      ← 3.1.x 归档（5 releases）
│   ├── CHANGELOG-3.2.md      ← 3.2.x 归档（47 releases）
│   ├── CHANGELOG-3.3.md      ← 3.3.x 归档（13 releases）
│   └── CHANGELOG-3.4.md      ← 3.4.x 归档（38 releases）
├── scripts/
│   ├── release.js            ← 发布脚本（含 changelog 生成步骤）
│   └── verify-commit.js      ← commit message 校验
└── .github/
    └── commit-convention.md  ← Angular Convention 规范文档
```

## 2.2 生成链路

```
开发者提交规范 message
    ↓
verify-commit.js 校验（commit-msg hook）
    ↓
git log 积累符合 Angular Convention 的提交
    ↓
scripts/release.js 发布时触发
    ↓
pnpm run changelog
    ↓
conventional-changelog -p angular -i CHANGELOG.md -s
    ↓
生成的 CHANGELOG.md 作为 release commit 提交
```

## 2.3 核心工具

### 依赖

```json
{
  "scripts": {
    "changelog": "conventional-changelog -p angular -i CHANGELOG.md -s"
  },
  "devDependencies": {
    "conventional-changelog": "^7.2.0",
    "conventional-changelog-angular": "^8.3.1"
  }
}
```

### 命令拆解

```
conventional-changelog -p angular -i CHANGELOG.md -s
                       │           │                    │
                       │           │                    └ -s：将结果写回同一个输入文件（same-file）
                       │           └ -i：读取现有 CHANGELOG.md 作为输入
                       └ -p：使用 Angular preset

生成的新版本条目会放在文件顶部，同时保留已有历史内容；这里不是把新条目追加到文件末尾。
```

**工作流程：**

1. 读取自上一个 SemVer tag 以来的 commit 历史
2. 按 Angular 规范解析 type / scope / subject / body / footer
3. 按 type 分组：`fix` → Bug Fixes、`feat` → Features、`perf` → Performance Improvements
4. 同 scope 合并，按字母排序
5. 生成 compare link + commit hash link + issue ref link
6. 追加到 `CHANGELOG.md`

## 2.4 输出格式

```markdown
## [3.5.35](https://github.com/vuejs/core/compare/v3.5.34...v3.5.35) (2026-05-27)

### Bug Fixes

***compiler-core:** avoid double processing v-for keys with v-memo
  ([#14861](https://github.com/vuejs/core/issues/14861))
  ([34a0ded](https://github.com/vuejs/core/commit/34a0ded4d...)), closes [#14859](https://github.com/vuejs/core/issues/14859)

***compiler-sfc:** resolve top-level exports from files registered as global types
  ([#14805](https://github.com/vuejs/core/issues/14805))
  ([3d077f2](https://github.com/vuejs/core/commit/3d077f2...))

### Performance Improvements

***reactivity:** skip type checks for cached proxies
  ([#14860](https://github.com/vuejs/core/issues/14860))
  ([5734fe9](https://github.com/vuejs/core/commit/5734fe97...))
```

### Type → 分组映射

| commit type | Changelog 分组 | 说明 |
| --- | --- | --- |
| `feat` | Features | 出现在 Changelog |
| `fix` | Bug Fixes | 出现在 Changelog |
| `perf` | Performance Improvements | 出现在 Changelog |
| `revert:` | Reverts | 出现在 Changelog |
| `docs` / `chore` / `refactor` / `style` / `test` | **不出现** | 被忽略 |
| 含 `BREAKING CHANGE:` | 始终出现 | 附带 Breaking Changes 说明 |

## 2.5 发布流程中的位置

```
scripts/release.js 执行流程
│
├── 1. isInSyncWithRemote()      检查本地与远程同步
├── 2. 选择/输入版本号           交互式选择（patc/minor/major/prerelease/custom）
├── 3. confirmRelease            确认发布
├── 4. runTestsIfNeeded()        检查 CI 状态 + 可选本地测试
├── 5. updateVersions()          更新所有 package.json 版本
├── 6. pnpm run changelog  ◀──  生成 CHANGELOG.md
├── 7. changelogOk prompt        人工审核（不满意 Ctrl+C 中断）
├── 8. pnpm install              更新 lockfile
├── 9. git commit                提交 release: v{x.y.z}
├── 10. 若传入 --publish：构建并 pnpm publish 到 npm
├── 11. 若未 --skipGit：git tag + git push
└── 12. 未传 --publish 时：提示由 GitHub Actions 完成发布
```

### changelog 生成代码（v3.5.35 的 release.js 第 184-198 行）

```jsx
// generate changelog
step('\nGenerating changelog...')
await run(`pnpm`, ['run', 'changelog'])

if (!skipPrompts) {
  const { yes: changelogOk } = await prompt({
    type: 'confirm',
    name: 'yes',
    message: `Changelog generated. Does it look good?`,
  })
  if (!changelogOk) return  // 中断发布，人工修正
}
```

## 2.6 端到端数据流

```
┌───────────────────────────────────────────────────────────┐
│  commit message                                           │
│  feat(compiler-core): add 'comments' option               │
│  fix(v-model): handle events on blur, close #28           │
└──────────────────┬────────────────────────────────────────┘
                   ↓
┌───────────────────────────────────────────────────────────┐
│  verify-commit.js 正则                                    │
│  /^(revert: )?(feat|fix|docs|...)(\(.+\))?: .{1,50}/     │
└──────────────────┬────────────────────────────────────────┘
                   ↓ ✅ 通过
┌───────────────────────────────────────────────────────────┐
│  git log 积累                                             │
│  feat(compiler-core): ...    ← type=feat → Features       │
│  docs: update README          ← 被忽略                    │
│  fix(v-model): ...            ← type=fix → Bug Fixes      │
│  perf(core): ...              ← type=perf → Performance   │
└──────────────────┬────────────────────────────────────────┘
                   ↓ release.js 触发
┌───────────────────────────────────────────────────────────┐
│  conventional-changelog -p angular -i CHANGELOG.md -s     │
│  ① git log --format=raw 读取                              │
│  ② 解析 type/scope/subject/body/footer                    │
│  ③ 按 type 分组 + scope 排序                              │
│  ④ 生成 compare link + hash link + issue ref              │
│  ⑤ 追加到 CHANGELOG.md                                    │
└──────────────────┬────────────────────────────────────────┘
                   ↓
┌───────────────────────────────────────────────────────────┐
│  CHANGELOG.md                                             │
│  ## [3.5.35](...v3.5.34...v3.5.35) (2026-05-27)          │
│  ### Bug Fixes              ← type=fix                    │
│  * **compiler-core:** ...   ← scope=compiler-core         │
└───────────────────────────────────────────────────────────┘
```

## 2.7 版本归档

- 根目录 `CHANGELOG.md` 始终是**当前主版本**
- 跨 minor/major 时，维护者会将上一条 minor 线的历史**手动归档**为 `changelogs/CHANGELOG-3.x.md`
- 归档步骤不在 `release.js` 中自动化，需判断时机

## 2.8 人工审核与 CI 发布的边界

- `release.js` 在本地生成 changelog 后提供 `Changelog generated. Does it look good?` 确认步骤；这是源码可以直接确认的人工审核点。
- 是否直接发布 npm 由 `--publish` 控制：传入时本地构建并发布；未传入时脚本在 push/tag 后提示通过 GitHub Actions 完成发布。
- “为什么采用这种分工”属于维护策略推断，不能仅凭脚本证明；因此不把质量把控、迁移指南或归档时机写成官方既定原因。

---

# 三、Vue 2 vs Vue 3 数组响应式

## 3.1 一句话总结

> Vue 2 依靠 `Object.defineProperty` 与 7 个变异方法包装来补足数组观测能力；Vue 3 依靠 `Proxy` 捕获索引与 `length` 等操作，并为部分数组方法增加 instrumentation，以处理依赖追踪、批处理和 raw/proxy 身份一致性。
> 

## 3.2 核心差异

| 维度 | Vue 2 | Vue 3 |
| --- | --- | --- |
| **底层 API** | `Object.defineProperty` | `Proxy` |
| **数组检测能力** | `Object.defineProperty` 本身无法拦截索引赋值和 `length`；Vue 2 通过包装 7 个变异方法补偿 | 通过 Proxy handler 拦截 `get`、`set`、`has`、`deleteProperty`、`ownKeys` 等关键操作 |
| **是否需要「改写」** | 对 7 个变异方法必须包装；索引赋值和 `length` 仍是限制 | 不修改数组原型；对部分方法做 instrumentation |
| **改写方式** | 替换 `.__proto__`，重写 7 个方法 | Proxy get 陷阱返回包装函数，不改变数组 |
| **改写目的** | 弥补能力缺口 | 防止死锁、精准追踪、保持引用 |

## 3.3 Vue 2：被动补丁

### `Object.defineProperty` 本身的盲区

| 操作 | 能否被检测？ |
| --- | --- |
| `arr[0] = 'new'` | ❌ 索引赋值 |
| `arr.length = 0` | ❌ length 修改 |
| `arr.push('x')` | ❌ |
| `arr.pop()` | ❌ |
| `arr.shift()` | ❌ |
| `arr.unshift('x')` | ❌ |
| `arr.splice(0, 1)` | ❌ |
| `arr.sort()` | ❌ |
| `arr.reverse()` | ❌ |

### 解决方案：替换原型链

```jsx
// Vue 2 源码简化示意
const arrayProto = Array.prototype
const arrayMethods = Object.create(arrayProto)

;['push','pop','shift','unshift','splice','sort','reverse'].forEach(method => {
  const original = arrayProto[method]
  Object.defineProperty(arrayMethods, method, {
    value: function (...args) {
      const result = original.apply(this, args)
      const ob = this.__ob__
      let inserted
      switch (method) {
        case 'push': case 'unshift': inserted = args; break
        case 'splice': inserted = args.slice(2); break
      }
      if (inserted) ob.observeArray(inserted)  // 新元素响应式
      ob.dep.notify()                           // 通知更新
      return result
    }
  })
})

function observe(arr) {
  arr.__proto__ = arrayMethods  // ← 替换原型
}
```

### 三大缺陷

1. **直接索引赋值不响应** — 需使用 `Vue.set(arr, index, value)`、`vm.$set(...)` 或 `splice`
2. **直接修改 `length` 不响应** — 通常需改用 `splice`
3. **数组增强有环境分支** — 支持 `__proto__` 时替换原型；不支持时会把增强方法定义到数组实例上

> `filter` / `concat` / `slice` 是非变异方法，不修改原数组，因此“不主动通知原数组更新”不是缺陷。把它们用于 computed 时，computed 仍会随其读取到的响应式依赖重新计算。
> 

## 3.4 Vue 3：主动优化

### Proxy 天然能力

```jsx
const arr = reactive([1, 2, 3])

arr.push(4)       // ✅ Proxy set(3, 4) + get(length)
arr[0] = 0        // ✅ Proxy set(0, 0)
arr.length = 0    // ✅ Proxy set(length, 0)
arr.concat([4])   // ✅ get(Symbol.isConcatSpreadable) + get(0,1,2...)
```

### 但仍需要数组方法拦截

Vue 3 在 Proxy get 陷阱中返回包装后的方法，目的**不是补能力，是优化**：

#### 优化 1：避免递归触发 / 无限循环（#2137）

`push`/`pop`/`shift`/`unshift`/`splice` 内部读写 `length`，Proxy 会同时 track 和 trigger，产生循环：

```
effect() → arr.push('x') → get(length) → track
                         → set(length) → trigger → effect() → ... ∞
```

**递归触发图示：**

```
┌───────────────────────────────┐
│  effect()                     │
│    arr.push('x') ──┐         │
│       ↓             │         │
│  get(length) ── track         │
│       ↓                       │
│  set(length) ── trigger ──────┘
│       ↑────────────── 无限循环
└───────────────────────────────┘
```

**解决方案：**

```jsx
function noTracking(self, method, args = []) {
  pauseTracking()       // 暂停依赖收集
  startBatch()          // 开启批处理
  const res = toRaw(self)[method].apply(self, args)
  endBatch()            // 结束批处理 → 一次集体更新
  resetTracking()       // 恢复依赖收集
  return res
}
```

#### 优化 2：身份敏感查找

```jsx
const obj = { name: 'test' }
const arr = reactive([obj])

// 若直接在 proxy 元素与 raw 参数之间比较，可能出现身份不一致；
// Vue 3 的 instrumentation 会在必要时转成 raw 再查，因此实际结果为 true。
arr.includes(obj)  // true
```

**解决方案：双次查找**

```jsx
function searchProxy(self, method, args) {
  const arr = toRaw(self)
  track(arr, TrackOpTypes.ITERATE, ARRAY_ITERATE_KEY)
  const res = arr[method](...args)           // 第一次：用 proxy args
  if ((res === -1 || res === false) && isProxy(args[0])) {
    args[0] = toRaw(args[0])                 // 转 raw 再查
    return arr[method](...args)
  }
  return res
}
```

#### 优化 3：迭代依赖追踪

统一用 `ARRAY_ITERATE_KEY` 语义化追踪”数组内容变了”：

```
arr.map(x => x.n) 时 → track(arr, ITERATE, ARRAY_ITERATE_KEY)

数组 push/splice 时 → trigger(arr, ITERATE, ARRAY_ITERATE_KEY)
→ 所有使用了 map/filter/forEach 的 computed/watch 重新计算
```

#### 优化 4：返回值包装

```jsx
const raw = reactive([{ name: 'a' }])
const result = raw.filter(x => true)
result[0]  // Proxy({ name: 'a' })  ← 仍是响应式
```

```jsx
function apply(self, method, fn, thisArg, wrappedRetFn, args) {
  const arr = shallowReadArray(self)
  const result = arr[method].call(arr, wrappedFn, thisArg)
  return needsWrap && wrappedRetFn
    ? wrappedRetFn(result)   // 对每个元素 toWrapped
    : result
}
```

## 3.5 全方位对比

| 维度 | Vue 2 | Vue 3 |
| --- | --- | --- |
| **底层 API** | `Object.defineProperty` | `Proxy` |
| **数组索引读写** | 读 ✅ 写 ❌ | 读 ✅ 写 ✅ |
| **`length` 修改** | ❌ | ✅ |
| **改写方法数** | 7 个 | 27 个显式 instrumentation（v3.5.35；其余方法回落到原生实现 + Proxy traps） |
| **改写方式** | 替换 `__proto__` | Proxy get 陷阱返回包装函数 |
| **改写目的** | 弥补能力缺口 | 防死锁、精准追踪、保引用 |
| **`arr[0] = x`** | ❌ 需 `$set` | ✅ |
| **`arr.length = 0`** | ❌ | ✅ |
| **`includes` 正确性** | N/A | ✅ 双次查找 |
| **push 死锁** | 不存在（defineProperty 不 track get） | 部分场景可能递归触发；用 `pauseTracking()` 避免收集 `length` 依赖 |
| **初始化性能** | 递归遍历每个属性，大数组慢 | 嵌套对象在读取时按需转为代理；实际性能仍取决于数据形态和访问模式 |
| **新增属性** | ❌ | ✅ |

## 3.6 实际代码差异

### Vue 2 — 数组索引与 `length` 需要 workaround

```jsx
const state = Vue.observable({ arr: ['a', 'b'] })

// ❌ 这两种写法不会触发 Vue 2 的更新
state.arr[0] = 'x'
state.arr.length = 0

// ✅ 使用框架 API 或变异方法
Vue.set(state.arr, 0, 'x')       // 组件中也可用 vm.$set(...)
state.arr.splice(0)

// filter 返回新数组；若在 computed 中读取 state.arr，仍会随依赖变化重算
const filtered = state.arr.filter(x => true)
```

### Vue 3 — 一切自然工作

```jsx
const arr = reactive(['a', 'b'])

arr[0] = 'x'             // ✅ 更新
arr.length = 0           // ✅ 更新
arr.push('c')            // ✅ 更新（批处理合并，不重复渲染）

const filtered = computed(() => arr.filter(x => true))
// ✅ 自动响应
```

## 3.7 社区常见误解

> “Vue 3 也重写了数组方法，所以和 Vue 2 一样”
> 

**错误。** Vue 3 的数组方法拦截不修改原型链：

- Vue 2：`arr.__proto__ = hackedPrototype`（对象被改变）
- Vue 3：`proxy.get = fn → return wrappedMethod`（纯行为代理）

```jsx
// 验证
const arr = reactive([1, 2, 3])
Object.getPrototypeOf(arr) === Array.prototype  // true（Vue 2 是 false）
```

## 3.8 哲学对比

|  | Vue 2 | Vue 3 |
| --- | --- | --- |
| **哲学** | 在 ES5 能力边界内，通过 getter/setter 与数组增强补偿 | 利用 Proxy 扩大可观测范围，并对数组方法做语义化优化 |
| **本质** | 兼容性补偿 | 基础拦截 + 方法级 instrumentation |
| **动机** | 受 ES5 API 能力约束 | 利用 ES2015 Proxy 能力 |
| **代价** | 索引/`length` 更新需特殊 API | 运行时实现更复杂，但业务侧写法更自然 |

---

# 四、结论与核验摘要

<aside>
✅

已按 `vuejs/core@v3.5.35` 的实际源码复核。提交 Hook 与 changelog 形成一条工程化链路；数组响应式是独立的运行时主题，不应被表述为与前两者直接联动。

</aside>

1. **Hook → Changelog**：`pre-commit` 负责暂存文件质量与 TypeScript 检查，`commit-msg` 约束提交格式；规范化的 `feat` / `fix` / `perf` 等提交再由 Angular preset 生成版本说明。
2. **发布边界**：版本号由发布者选择；changelog 在本地生成并人工确认；是否本地发布 npm 取决于 `--publish`，否则提示交给 GitHub Actions。
3. **数组响应式**：Vue 2 通过 getter/setter 与 7 个变异方法增强补偿 ES5 限制；Vue 3 通过 Proxy 观察索引与 `length`，并用 27 个显式 instrumentation 处理迭代依赖、批处理和 raw/proxy 身份问题。

## 本次主要修正

- 提交类型由“14 种”改为 **15 种（含 `release`）**。
- 说明 `.{1,50}` 因正则没有 `$`，**不构成严格的 50 字符上限**。
- 将 CI 类型检查从错误的 `vue-tsc -b` 改为实际的 `pnpm run check` + `pnpm run test-dts`。
- 更正 `-s` 为 same-file 写回，并说明新版本条目位于 changelog 顶部。
- 更正发布流程中的 `--publish` / `--skipGit` 条件分支。
- 修正 Vue 2 的 `$set` 用法、`filter` 结论、Vue 3 `includes` 示例，以及 instrumentation 数量。

## 参考源码（固定版本）

- [根 package.json：scripts、simple-git-hooks、lint-staged 与依赖[1]](https://github.com/vuejs/core/blob/v3.5.35/package.json)
- [提交信息校验脚本[2]](https://github.com/vuejs/core/blob/v3.5.35/scripts/verify-commit.js)
- [提交规范[3]](https://github.com/vuejs/core/blob/v3.5.35/.github/commit-convention.md)
- [CI test workflow[4]](https://github.com/vuejs/core/blob/v3.5.35/.github/workflows/test.yml)
- [发布脚本[5]](https://github.com/vuejs/core/blob/v3.5.35/scripts/release.js)
- [Vue 3 数组 instrumentation[6]](https://github.com/vuejs/core/blob/v3.5.35/packages/reactivity/src/arrayInstrumentations.ts)
- [Vue 3 基础 Proxy handlers[7]](https://github.com/vuejs/core/blob/v3.5.35/packages/reactivity/src/baseHandlers.ts)
- [Vue 2.7.16 数组增强实现[8]](https://github.com/vuejs/vue/blob/v2.7.16/src/core/observer/array.ts)

---