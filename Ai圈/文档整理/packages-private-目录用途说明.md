# packages-private 目录用途说明

本文说明 Vue 源码仓库中 `packages-private` 的用途、各子工程的职责，以及开发时如何选择相应工具。

依据：本地仓库 `D:/ProjectCode/vue3`，分支 `lmy`，提交 `43685759a866492c806aa13407b8a47b9e2be1c3`；整理日期：2026-09-02。

## 整体定位

`packages-private` 是 Vue 仓库内部的开发、调试和类型验证工具集合。它和 `packages` 一起纳入 pnpm workspace，可以通过 `workspace:*` 依赖本地 Vue 包。

当前包含五个子工程，均在各自的 `package.json` 中设置了 `"private": true`，用于仓库内部协作，不作为独立 npm 包发布。“private” 表示包的发布属性，不代表代码保密；其中的调试工具仍可构建为网站。

`packages` 主要承载 Vue 的运行时、响应式、编译器等实现；`packages-private` 则提供使用这些实现的测试样例和调试入口。例如：修改编译器后，通过 Template Explorer 查看输出；修改类型定义后，通过 dts 测试检查兼容性。

## 五个子工程分别做什么

| 子目录 | 主要用途 | 典型使用场景 |
| --- | --- | --- |
| `dts-test` | 检查 Vue API 的 TypeScript 类型推断、约束和错误提示是否符合预期。 | 修改 props、emits、ref、组件类型或泛型后，补充类型回归用例。 |
| `dts-built-test` | 模拟依赖 Vue 类型的外部库，生成声明文件并验证相关类型边界情况。 | 检查组件自定义属性、模块增强等在声明生成和消费时是否保留。 |
| `sfc-playground` | 提供基于 `@vue/repl` 的单文件组件交互调试环境。 | 编写和运行 `.vue` 示例，复现模板、脚本、样式及运行时行为。 |
| `template-explorer` | 实时查看模板编译后的输出。 | 观察指令、表达式、静态提升等语法如何转换为渲染代码。 |
| `vite-debug` | 提供接近实际项目的 Vite 与 `@vitejs/plugin-vue` 调试环境。 | 复现仅在 Vite 工程或 Vue 插件集成中出现的问题。 |

## 类型测试：dts-test 与 dts-built-test

`dts-test` 检查的是编译期类型行为。它与执行组件、响应式逻辑的运行时单元测试互补，不能互相替代。

同一批类型用例可在不同配置下解析 Vue：

- `packages-private/tsconfig.json` 继承根配置，并包含当前私有工程目录；继承的路径别名将 `vue` 和 `@vue/*` 指向源码，供相应 TypeScript 工程检查使用。
- `dts-test/tsconfig.test.json` 使用独立配置和 Node 模块解析，检查通过包入口解析的类型，因此需要先构建 Vue 的声明文件。

`dts-built-test` 则提供一个“外部库”样例：其源码使用 `defineComponent` 定义组件，测试侧通过扩展 `ComponentCustomProps`，检查自定义属性类型是否被保留。该包配置了仅输出声明文件的 TypeScript 构建。

当前根脚本的执行顺序是：

```
pnpm test-dts
  → pnpm build-dts
      → 生成并打包 Vue 核心包的声明文件
  → pnpm test-dts-only
      → 编译 dts-built-test，输出声明文件
      → 使用 dts-test/tsconfig.test.json 执行类型检查
```

**当前配置与 README 的差异：**

- `dts-test/README.md` 仍写着根 `pnpm check` 会覆盖该目录，但当前根 `tsconfig.json` 的 `include` 没有直接纳入 `packages-private`。不要将 `pnpm check` 通过视为全部 dts 用例已通过；CI 也分别执行 `check` 和 `test-dts`。
- `dts-built-test/README.md` 对构建时机的描述与当前脚本不同：现在由 `test-dts-only` 先编译该样例包。
- 当前 `built.test-d.ts` 导入的是 `dts-built-test/src/index`，而非包根声明入口。它验证了相关类型场景，但不能仅凭 README 断言该用例直接消费了样例包的 `dist/index.d.ts`。

以上说明用于准确理解当前仓库，本次未修改这些配置或 README。

## 三种调试工具如何选择

**Template Explorer：关注模板编译。** 输入模板并观察编译结果，适合阅读或修改 `compiler-core`、`compiler-dom` 时使用。本地开发入口是 `local.html`；README 中的 `index.html` 使用 CDN 依赖，二者用途不同。

**SFC Playground：关注完整单文件组件。** 可以在交互环境中验证组件行为。根脚本 `dev-sfc` 会先检查必要的编译器构建产物，缺失时构建，再并行启动相关包的开发构建和 Vite 服务。构建网站使用专门的 `build-sfc-playground` 脚本。

**Vite Debug：关注真实构建工具集成。** 配置直接使用 `@vitejs/plugin-vue`，README 明确要求 Vue 解析到构建产物而非源码。定位 Vite 插件或产物入口问题时优先使用它；修改 Vue 源码后，需要更新相关构建产物才能看到效果。

## 常用命令

以下命令均在仓库根目录执行；先按仓库要求准备 Node、pnpm 并安装依赖。这里根据脚本说明命令用途，本次未启动这些服务或重新运行类型测试。

| 目标 | 命令 | 说明 |
| --- | --- | --- |
| 完整类型声明测试 | `pnpm test-dts` | 先构建 Vue 类型，再执行样例包构建和类型测试。 |
| 仅重新执行类型测试 | `pnpm test-dts-only` | 前提是 Vue 的声明文件已经构建且与源码一致。 |
| 启动 SFC Playground | `pnpm dev-sfc` | 使用根脚本准备依赖产物并启动开发环境。 |
| 构建 SFC Playground | `pnpm build-sfc-playground` | 构建相关 Vue 产物和 Playground 网站。 |
| 启动模板编译调试 | `pnpm dev-compiler` | 等待编译完成，在另一终端执行 `pnpm open` 打开本地页面。 |
| 启动 Vite Debug | `pnpm --filter vite-debug dev` | 依赖相关 Vue 构建产物；首次使用可先执行 `pnpm build`。 |

通用构建脚本会在全量构建或发布模式下跳过标记为 private 的包。因此，不应把 `pnpm build` 理解为会同时构建所有 Playground 网站；这些工程应使用各自的专用命令。

## 开发时怎样使用这个目录

- 修改 Vue API 类型：在 `dts-test` 添加类型用例，并执行 `pnpm test-dts`。
- 需要模拟组件库的声明输出：检查或扩展 `dts-built-test`，同时确认测试的导入路径确实覆盖预期的源码或声明产物。
- 研究模板生成代码：使用 `template-explorer`。
- 调试单文件组件的整体效果：使用 `sfc-playground`。
- 问题依赖 Vite 插件、打包环境或 Vue 产物入口：使用 `vite-debug`。

正常使用 npm 安装的 Vue 开发业务项目，无需引入这个目录。维护本仓库时则应保留它：workspace 配置、根脚本和 CI 都依赖其中的工具或类型测试。

## 查证依据

以下为本次实际读取的本地文件，均相对于前述提交内容核对：

- 工作区和命令入口：`D:/ProjectCode/vue3/pnpm-workspace.yaml`、`D:/ProjectCode/vue3/package.json`。
- 五个私有工程各自的 README 与 package.json，位于 `D:/ProjectCode/vue3/packages-private` 下。
- 类型解析与构建：`D:/ProjectCode/vue3/tsconfig.json`、`D:/ProjectCode/vue3/packages-private/tsconfig.json`、`D:/ProjectCode/vue3/tsconfig.build.json`、`D:/ProjectCode/vue3/rollup.dts.config.js`。
- 类型测试细节：`D:/ProjectCode/vue3/packages-private/dts-test/tsconfig.test.json`、`D:/ProjectCode/vue3/packages-private/dts-test/built.test-d.ts`、`D:/ProjectCode/vue3/packages-private/dts-built-test/tsconfig.json`、`D:/ProjectCode/vue3/packages-private/dts-built-test/src/index.ts`。
- 开发和 CI：`D:/ProjectCode/vue3/scripts/build.js`、`D:/ProjectCode/vue3/scripts/dev.js`、`D:/ProjectCode/vue3/scripts/pre-dev-sfc.js`、`D:/ProjectCode/vue3/.github/workflows/test.yml`。
- 调试工具配置：`D:/ProjectCode/vue3/packages-private/vite-debug/vite.config.ts`、`D:/ProjectCode/vue3/packages-private/sfc-playground/vite.config.ts`。

[文档整理](../%E6%96%87%E6%A1%A3%E6%95%B4%E7%90%86.md)