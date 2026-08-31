# Monorepo 使用总结与原理

<aside>
📦 Monorepo（单仓库）是一种将多个相关项目放在同一个代码仓库中的开发策略。本文从原理到实践，全面总结 Monorepo 的核心概念、优势挑战、主流工具链以及最佳实践。

</aside>

## 一、什么是 Monorepo

Monorepo（Monolithic Repository）指的是将多个项目或包的源码放在同一个版本控制仓库中管理的策略。与之相对的是 Multirepo（多仓库）。

**关键区分：Monorepo ≠ Monolith（单体应用）**。Monorepo 只是代码组织方式，代码本身仍然可以是模块化、解耦的。

### Monorepo 的典型目录结构

```jsx
my-monorepo/
├── package.json              # 根 package.json（workspaces 配置）
├── pnpm-workspace.yaml       # pnpm workspace 配置
├── packages/                 # 可发布的公共包
│   ├── core/
│   │   ├── src/
│   │   ├── package.json
│   │   └── vitest.config.ts
│   ├── utils/
│   ├── ui/
│   └── types/
├── apps/                     # 应用入口
│   ├── web/                  # 网页应用
│   │   ├── src/
│   │   ├── package.json
│   │   └── vite.config.ts
│   ├── mobile/               # 移动端
│   └── docs/                 # 文档站点
├── tools/                    # 构建工具/脚本
│   ├── eslint-config/
│   └── ts-config/
├── .github/                  # CI/CD 配置
├── tsconfig.base.json        # 共享 TS 配置
├── vitest.workspace.json     # 测试工作区配置
└── turbo.json                # Turborepo 管道配置
```

---

## 二、Monorepo 的核心原理

### 1. 单一版本库（Single Source of Truth）

所有代码都在一个仓库里，提交历史统一、代码审查统一、发布流程统一。开发者在同一个 PR 中就可以修改多个包，跨包协作零摩擦。

### 2. Workspace（工作区）协议

现代包管理器通过 workspace 协议实现 Monorepo 的核心依赖管理：

```bash
# 在包的 package.json 中
{
  "name": "@my-app/web",
  "dependencies": {
    "@my-app/core": "workspace:*",     # 锁定本地最新版本
    "@my-app/utils": "workspace:^1.2"  # 语义化版本
  }
}
```

workspace: 协议的作用：

- 告诉包管理器：这个依赖要在本仓库中找，不要去 registry 下载
- 发布时自动替换为实际版本号（如 workspace:^ → ^1.0.0）
- 确保本地开发时始终使用源码版本，不需要 link

### 3. 依赖提升与隔离

Monorepo 的核心机制是依赖去重。公共依赖会被提升到根 node_modules，不同版本的依赖各自保留：

- **公共的 React、TypeScript 等，只安装一份在根目录**
- 各包独有的依赖保留在各自 node_modules（pnpm）或扁平化提升（npm）
- **pnpm 的严格模式保证每个包只能访问自己声明的依赖**

### 4. 构建缓存与任务编排

大型 Monorepo 必须有构建缓存和任务编排系统，避免每次构建所有包：

- **按依赖拓扑排序构建任务（拓扑排序）**
- **内容哈希缓存：输入不变则跳过构建**
- 增量构建：只构建变更的包及其依赖链
- 并行执行：无依赖关系的包并行构建

### 5. 软链接 / 硬链接（Symlink）

本地包之间通过符号链接关联，包 A 引用包 B 时，实际指向 B 的源码目录。修改 B 的代码，A 立即生效（类似 npm link）：

```jsx
# pnpm 创建的 node_modules 结构
node_modules/
├── @my-app
│   ├── core -> .pnpm/@my-app+core@1.0.0/node_modules/@my-app/core
│   │                      # ↑ 硬链接指向全局 store
│   └── utils -> ../../packages/utils
│                      # ↑ 开发时指向本地源码
└── .pnpm/...
```

---

## 三、为什么选择 Monorepo

### ✅ 优势

- **代码共享与复用**

多个应用共享 UI 组件库、工具函数、类型定义等。不需要发布到 npm 就能引用，改动立刻生效。

- **原子性提交**

跨包修改在一个 PR 中完成。修改 API 的同时更新所有使用者，不存在「先发布 A 再更新 B」的协调问题。

- **统一的构建/测试/发布**

一套 ESLint 规则、一套 TypeScript 配置、一套 CI 流水线。减少维护多个仓库的配置负担。

- **依赖管理更高效**

公共依赖只安装一次，节省磁盘空间。版本冲突更容易发现和解决。

- **重构成本更低**

跨包重构或 API 变更时，IDE 可以在同一个仓库中完成全局搜索和替换。类型检查覆盖所有依赖包。

- **团队协作更透明**

所有代码在一个仓库中，新成员更容易了解整体架构。代码审查可以跨项目进行。

### ❌ 挑战与缺点

- **Git 仓库膨胀**

大量代码和提交历史会让 git 操作变慢，需要 Git LFS、浅克隆等策略优化。

- **构建流水线复杂度**

需要构建缓存、增量构建、智能 CI 流水线，否则每次 CI 构建全量代码会很慢。

- **权限管理困难**

Git 本身的权限是仓库级别的，不能对不同目录设置不同权限。需要用 CODEOWNERS 等文件来管理。

- **学习曲线**

需要理解 workspace 协议、构建编排、发布策略等概念，新手上手成本比单包项目高。

- **工具链依赖**

需要 Turborepo / Nx / Rush 等工具来管理，增加了技术栈复杂度。

---

## 四、主流 Monorepo 工具链对比

| **工具** | **类型** | **语言** | **核心特性** | **成熟度** |
| --- | --- | --- | --- | --- |
| pnpm workspaces | 包管理器 | JS/TS | 严格隔离 + Filter + Catalog | ⭐⭐⭐⭐⭐ |
| Turborepo | 构建编排 | Go | 缓存 + 管道 + 远程缓存 | ⭐⭐⭐⭐⭐ |
| Nx | 构建编排 | TS/Go | 增量构建 + 图分析 + 生成器 | ⭐⭐⭐⭐⭐ |
| Rush | 包管理器 | TS | 微软出品 + 门禁机制 | ⭐⭐⭐⭐ |
| Yarn workspaces | 包管理器 | JS/TS | PnP + 约束协议 | ⭐⭐⭐⭐ |
| Lerna | 发布工具 | JS | 老牌 + 版本发布管理 | ⭐⭐⭐ |
| Bazel | 构建系统 | Java/Starlark | Google 出品 + 精确缓存 | ⭐⭐⭐⭐ |
| Moonrepo | 构建编排 | Rust | 新一代 + 高性能 | ⭐⭐⭐ |

### 核心推荐组合（2025年主流方案）

- 包管理器：**pnpm（推荐）或 yarn v4**
- 构建编排：**Turborepo 或 Nx**
- 发布管理：**Changesets 或 semantic-release**
- CI/CD：**GitHub Actions + Turborepo 远程缓存**

---

## 五、pnpm Workspace + Turborepo 实战

### 1. 项目初始化

```bash
mkdir my-monorepo && cd my-monorepo
pnpm init
```

### 2. 配置 pnpm workspace

```yaml
# pnpm-workspace.yaml
packages:
  - 'apps/*'
  - 'packages/*'
  - 'tools/*'
  - '!**/dist/**'
  - '!**/node_modules/**'
```

### 3. 配置根 package.json

```jsx
{
  "name": "my-monorepo",
  "private": true,
  "scripts": {
    "dev": "turbo dev",
    "build": "turbo build",
    "test": "turbo test",
    "lint": "turbo lint",
    "format": "prettier --write .",
    "changeset": "changeset",
    "release": "turbo build && changeset publish"
  },
  "devDependencies": {
    "turbo": "^2.5.0",
    "typescript": "^5.7.0",
    "prettier": "^3.5.0",
    "@changesets/cli": "^2.28.0"
  },
  "packageManager": "pnpm@9.15.0",
  "engines": {
    "node": ">=20"
  }
}
```

### 4. 配置 Turborepo 管道

```jsx
{
  "$schema": "https://turbo.build/schema.json",
  "globalDependencies": ["tsconfig.base.json"],
  "pipeline": {
    "build": {
      "dependsOn": ["^build"],        // 先构建依赖
      "outputs": ["dist/**", ".next/**"],
      "inputs": ["src/**", "tsconfig.json"],
      "cache": true
    },
    "test": {
      "dependsOn": ["build"],
      "inputs": ["src/**", "tests/**"],
      "outputs": []
    },
    "lint": {
      "dependsOn": ["^build"],
      "outputs": []
    },
    "dev": {
      "cache": false,
      "persistent": true
    },
    "typecheck": {
      "dependsOn": ["^build"]
    }
  }
}
```

### 5. 创建子包结构

```jsx
mkdir -p packages/{core,utils,ui}
mkdir -p apps/{web,mobile,docs}
```

每个子包的 package.json 示例：

```jsx
// packages/core/package.json
{
  "name": "@my-app/core",
  "version": "0.1.0",
  "private": false,
  "main": "./dist/index.js",
  "module": "./dist/index.mjs",
  "types": "./dist/index.d.ts",
  "scripts": {
    "build": "tsup src/index.ts --format esm,cjs",
    "test": "vitest run",
    "dev": "tsup src/index.ts --watch"
  },
  "dependencies": {
    "@my-app/utils": "workspace:*"
  },
  "devDependencies": {
    "typescript": "^5.7.0",
    "tsup": "^8.4.0",
    "vitest": "^3.5.0"
  }
}
```

```jsx
// apps/web/package.json
{
  "name": "@my-app/web",
  "version": "0.1.0",
  "private": true,
  "scripts": {
    "dev": "vite",
    "build": "vite build",
    "test": "vitest run"
  },
  "dependencies": {
    "@my-app/core": "workspace:*",
    "@my-app/ui": "workspace:*",
    "react": "^19.0.0"
  }
}
```

### 6. 配置 TypeScript

```jsx
// tsconfig.base.json
{
  "compilerOptions": {
    "target": "ES2022",
    "module": "ESNext",
    "moduleResolution": "bundler",
    "lib": ["ES2022", "DOM"],
    "strict": true,
    "esModuleInterop": true,
    "skipLibCheck": true,
    "forceConsistentCasingInFileNames": true,
    "resolveJsonModule": true,
    "isolatedModules": true,
    "declaration": true,
    "declarationMap": true,
    "sourceMap": true
  }
}
```

```jsx
// packages/core/tsconfig.json
{
  "extends": "../../tsconfig.base.json",
  "compilerOptions": {
    "outDir": "./dist",
    "rootDir": "./src"
  },
  "include": ["src"]
}
```

### 7. 日常开发命令

```bash
# 安装所有依赖
pnpm install

# 给某个子包安装依赖
pnpm --filter @my-app/web add react-router-dom
pnpm --filter @my-app/core add -D vitest

# 运行某个子包的脚本
pnpm --filter @my-app/core run build

# 运行所有包的 build
pnpm -r run build

# 只运行变更的子包
pnpm --filter="[origin/main]" run build

# 开发模式（Turborepo 编排）
turbo dev

# 清理所有 dist
pnpm -r exec rm -rf dist
```

---

## 六、版本控制与发布策略

### 1. Changesets — 推荐的 Monorepo 发布方案

Changesets 是目前最流行的 Monorepo 发布工具，与 pnpm 深度集成：

```bash
# 初始化 changesets
pnpm changeset init

# 记录变更（交互式选择影响范围和版本类型）
pnpm changeset

# 升级版本号 + 生成 changelog
pnpm changeset version

# 发布
pnpm changeset publish
```

### 2. 版本策略选择

| **策略** | **描述** | **适用场景** |
| --- | --- | --- |
| 独立版本（Independent） | 每个包独立管理版本号 | 包之间无强依赖关系 |
| 统一版本（Lockstep） | 所有包使用同一个版本号 | 框架/工具库（如 React、Vue） |
| 按语义版本 | major/minor/patch 按变更类型自动计算 | 推荐大多数项目使用 |

### 3. Changelog 规范

```jsx
# .changeset/config.json
{
  "$schema": "https://unpkg.com/@changesets/config/schema.json",
  "changelog": "@changesets/cli/changelog",
  "commit": true,
  "fixed": [],
  "linked": [["@my-app/*"]],
  "access": "public",
  "baseBranch": "main",
  "updateInternalDependencies": "patch",
  "ignore": ["@my-app/docs"]
}
```

---

## 七、CI/CD 配置（GitHub Actions + Turborepo）

```yaml
# .github/workflows/ci.yml
name: CI

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  ci:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 2  # 需要足够深度来对比变更

      - uses: pnpm/action-setup@v4
        with:
          version: 9

      - uses: actions/setup-node@v4
        with:
          node-version: 20
          cache: 'pnpm'

      - name: Install dependencies
        run: pnpm install --frozen-lockfile

      - name: Turborepo cache
        uses: actions/cache@v4
        with:
          path: .turbo
          key: turbo-${{ runner.os }}-${{ github.sha }}
          restore-keys: |
            turbo-${{ runner.os }}-

      - name: Lint
        run: pnpm lint

      - name: Type check
        run: pnpm -r run typecheck

      - name: Build
        run: pnpm build

      - name: Test
        run: pnpm test
```

---

## 八、Monorepo 最佳实践

### 1. 目录结构规范

- 明确区分 packages（可发布包）和 apps（应用）
- 使用 @scope/package 命名空间，避免冲突
- 统一 scripts 命令命名（build / dev / test / lint / typecheck）

### 2. 依赖管理

- **使用 frozen-lockfile 确保 CI 一致性**
- 公共开发依赖放在根 devDependencies（TypeScript、ESLint 等）
- 各包独有的运行时依赖放在各自的 package.json
- 定期使用 pnpm up --latest 更新依赖版本
- 使用 pnpm audit 检查安全漏洞

### 3. TypeScript 配置

- **根目录放 tsconfig.base.json，各包继承它**
- 使用项目引用（Project References）提高类型检查性能
- paths 和 references 配合，IDE 跳转精准

### 4. 构建优化

- **配置好 Turborepo 的 pipeline dependsOn 关系**
- 启用远程缓存（Vercel Remote Cache 或自定义）
- 使用 tsup / esbuild 等快速打包工具（而非 tsc）
- 按需构建：CI 只构建变更包及依赖链

### 5. 测试策略

- **单元测试就近写在每个包中（vitest）**
- 集成测试在 apps 层或专门的测试包中
- 使用 vitest workspace 实现所有包统一测试

```jsx
// vitest.workspace.json
[
  "packages/*",
  "apps/*"
]
```

### 6. Git 策略

- **使用浅克隆 + sparse checkout 加速 CI（fetch-depth: 0 有争议）**
- CODEOWNERS 管理代码审查责任人
- 约定式提交（Conventional Commits）：feat / fix / chore / docs

```jsx
# .github/CODEOWNERS
# 全局默认
* @team-core

# 特定包
packages/ui/ @team-ui
apps/mobile/ @team-mobile
docs/ @team-docs
```

### 7. 性能优化

- **Git 大文件用 Git LFS 管理**
- 定期清理 git 历史（git gc）
- CI 中使用 Turborepo 远程缓存 + pnpm store 缓存
- 大型 Monorepo 考虑使用 Bazel 或 Nx 的高级缓存策略

---

## 九、知名厂商的 Monorepo 实践

| **公司** | **仓库规模** | **工具链** | **亮点** |
| --- | --- | --- | --- |
| Google | 数十亿行代码 | Bazel（自研） | 所有代码一个仓库，全球最大 |
| Microsoft | 数百万包 | Rush + Lage | Azure SDK 全量 Monorepo |
| Vercel | 开源 | Turborepo + pnpm | Next.js 自身使用 |
| Meta | 百万级 | Buck（自研） | React、Jest 等都在一个仓库 |
| 字节跳动 | 大型 | 自研 + pnpm | 国内 Monorepo 最早实践者 |
| Vue/Nuxt | 中型 | pnpm + Rollup | 核心库 + 生态包统一管理 |
| Babel | 中型 | Yarn + Lerna | 经典 Monorepo 案例 |

---

## 十、不同规模的选型建议

### 小型项目（2-5 人，2-5 个包）

```jsx
工具选型：
- pnpm workspaces（够用）
- 不需要 Turborepo / Nx
- 手动管理构建顺序即可
```

- 只需 pnpm -r run build（按拓扑顺序自动构建）
- package.json 中配置好 scripts 即可
- 不需要复杂的构建编排工具

### 中型项目（5-20 人，5-20 个包）

```jsx
工具选型：
- pnpm workspaces + Turborepo
- Changesets 管理发布
- GitHub Actions CI
```

- Turborepo 的缓存可以节省 50-80% 的构建时间
- Changesets 自动化版本管理和 changelog 生成
- 需要 CODEOWNERS 管理代码归属

### 大型项目（20+ 人，20+ 个包）

```jsx
工具选型：
- pnpm workspaces + Nx / Bazel
- Remote Caching（远程缓存）
- 自研或定制化 CI 流水线
```

- 需要精确的增量构建和分布式缓存
- 可能需要门禁机制确保包版本合规
- 建议有专门的工程效率团队维护

---

## 十一、总结

<aside>
🔑 Monorepo 不是银弹。它解决的是多项目协作中的依赖管理和版本协调问题，但也带来了构建复杂度和工具链依赖等新挑战。

</aside>

**核心原则：**根据团队规模和技术栈选择合适的工具链，不要为了 Monorepo 而 Monorepo。

**推荐方案（2025年）：pnpm + Turborepo + Changesets + GitHub Actions**是目前社区最成熟、体验最好的组合。

参考链接：
pnpm Workspace 文档: https://pnpm.io/workspaces
Turborepo 文档: https://turbo.build/repo/docs
Changesets: https://github.com/changesets/changesets
Nx 文档: https://nx.dev
Google 的 Monorepo: https://cacm.acm.org/magazines/2016/7/204032-why-google-stores-billions-of-lines-of-code-in-a-single-repository

- 明确区分 packages（可发布包）和 apps（应用）
- 使用 @scope/package 命名空间，避免冲突
- 统一 scripts 命令命名（build / dev / test / lint / typecheck）

### 2. 依赖管理

- **使用 frozen-lockfile 确保 CI 一致性**
- 公共开发依赖放在根 devDependencies（TypeScript、ESLint 等）
- 各包独有的运行时依赖放在各自的 package.json
- 定期使用 pnpm up --latest 更新依赖版本
- 使用 pnpm audit 检查安全漏洞

### 3. TypeScript 配置

- **根目录放 tsconfig.base.json，各包继承它**
- 使用项目引用（Project References）提高类型检查性能
- paths 和 references 配合，IDE 跳转精准

### 4. 构建优化

- **配置好 Turborepo 的 pipeline dependsOn 关系**
- 启用远程缓存（Vercel Remote Cache 或自定义）
- 使用 tsup / esbuild 等快速打包工具（而非 tsc）
- 按需构建：CI 只构建变更包及依赖链

### 5. 测试策略

- **单元测试就近写在每个包中（vitest）**
- 集成测试在 apps 层或专门的测试包中
- 使用 vitest workspace 实现所有包统一测试

```jsx
// vitest.workspace.json
[
  "packages/*",
  "apps/*"
]
```

### 6. Git 策略

- **使用浅克隆 + sparse checkout 加速 CI（fetch-depth: 0 有争议）**
- CODEOWNERS 管理代码审查责任人
- 约定式提交（Conventional Commits）：feat / fix / chore / docs

```jsx
# .github/CODEOWNERS
# 全局默认
* @team-core

# 特定包
packages/ui/ @team-ui
apps/mobile/ @team-mobile
docs/ @team-docs
```

### 7. 性能优化

- **Git 大文件用 Git LFS 管理**
- 定期清理 git 历史（git gc）
- CI 中使用 Turborepo 远程缓存 + pnpm store 缓存
- 大型 Monorepo 考虑使用 Bazel 或 Nx 的高级缓存策略

---

## 九、知名厂商的 Monorepo 实践

| **公司** | **仓库规模** | **工具链** | **亮点** |
| --- | --- | --- | --- |
| Google | 数十亿行代码 | Bazel（自研） | 所有代码一个仓库，全球最大 |
| Microsoft | 数百万包 | Rush + Lage | Azure SDK 全量 Monorepo |
| Vercel | 开源 | Turborepo + pnpm | Next.js 自身使用 |
| Meta | 百万级 | Buck（自研） | React、Jest 等都在一个仓库 |
| 字节跳动 | 大型 | 自研 + pnpm | 国内 Monorepo 最早实践者 |
| Vue/Nuxt | 中型 | pnpm + Rollup | 核心库 + 生态包统一管理 |
| Babel | 中型 | Yarn + Lerna | 经典 Monorepo 案例 |

---

## 十、不同规模的选型建议

### 小型项目（2-5 人，2-5 个包）

```jsx
工具选型：
- pnpm workspaces（够用）
- 不需要 Turborepo / Nx
- 手动管理构建顺序即可
```

- 只需 pnpm -r run build（按拓扑顺序自动构建）
- package.json 中配置好 scripts 即可
- 不需要复杂的构建编排工具

### 中型项目（5-20 人，5-20 个包）

```jsx
工具选型：
- pnpm workspaces + Turborepo
- Changesets 管理发布
- GitHub Actions CI
```

- Turborepo 的缓存可以节省 50-80% 的构建时间
- Changesets 自动化版本管理和 changelog 生成
- 需要 CODEOWNERS 管理代码归属

### 大型项目（20+ 人，20+ 个包）

```jsx
工具选型：
- pnpm workspaces + Nx / Bazel
- Remote Caching（远程缓存）
- 自研或定制化 CI 流水线
```

- 需要精确的增量构建和分布式缓存
- 可能需要门禁机制确保包版本合规
- 建议有专门的工程效率团队维护

---

## 十一、总结

<aside>
🔑 Monorepo 不是银弹。它解决的是多项目协作中的依赖管理和版本协调问题，但也带来了构建复杂度和工具链依赖等新挑战。

</aside>

**核心原则：**根据团队规模和技术栈选择合适的工具链，不要为了 Monorepo 而 Monorepo。

**推荐方案（2025年）：pnpm + Turborepo + Changesets + GitHub Actions**是目前社区最成熟、体验最好的组合。

参考链接：
pnpm Workspace 文档: https://pnpm.io/workspaces
Turborepo 文档: https://turbo.build/repo/docs
Changesets: https://github.com/changesets/changesets
Nx 文档: https://nx.dev
Google 的 Monorepo: https://cacm.acm.org/magazines/2016/7/204032-why-google-stores-billions-of-lines-of-code-in-a-single-repository