# death-note

Vue 3 + TypeScript + Vite 标准项目模板（依赖全部升级至最新版）。

## 技术栈

| 类别 | 技术 | 版本 |
| ---- | ---- | ---- |
| 框架 | Vue | ^3.5.41 |
| 路由 | vue-router | ^5.2.0 |
| 构建 | Vite | ^8.2.2 |
| 语言 | TypeScript | ~6.0.3 |
| 样式 | UnoCSS | ^66.8.0 |
| Lint | ESLint (flat config) | ^10.8.1 |
| 类型检查 | vue-tsc | ^3.3.10 |
| Markdown | marked + marked-highlight + highlight.js | latest |
| 3D | three（类型 @types/three） | latest |

> TypeScript 保持 6.x：`typescript-eslint@8.67` 的 peer 约束为 `>=4.8.4 <6.1.0`，
> 尚不支持 TS 7.0。待生态跟进后可将 `typescript` 升级至 `^7.0.2`。

## 快速开始

```bash
pnpm install
pnpm dev        # 启动开发服务器
pnpm build      # 生产构建
pnpm preview    # 预览构建产物
pnpm lint       # ESLint 检查
pnpm type-check # vue-tsc 类型检查
```

## 项目结构

```
├── index.html
├── vite.config.ts        # Vite + UnoCSS 配置（含 shortcuts/主题/预检样式）
├── eslint.config.js      # ESLint flat config（JS + TS + Vue）
├── tsconfig.json         # TS 严格模式 + @/* 路径别名
├── pnpm-workspace.yaml   # pnpm 构建允许清单
└── src/
    ├── main.ts           # 入口，挂载 UnoCSS 与路由
    ├── App.vue           # 根组件（布局 + 导航）
    ├── env.d.ts          # 类型声明（.vue 模块、three、vite/client）
    ├── router/           # vue-router 路由
    └── views/            # 页面组件（HomeView / AboutView）
```

## 说明

- 样式方案为 UnoCSS（`virtual:uno.css`），预设 `presetUno` + `presetAttributify`，
  并保留原项目的自定义 shortcuts 与暗色主题预检样式。
- 构建产物输出至 `dist/`（原 `death-note/` 目录为历史构建产物，已 gitignore）。
- `src/index.html` 为误写文件，需删除（待确认）。
