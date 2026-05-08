# Death Note

一个基于 Vue 3 的个人知识库应用，包含 LeetCode 题解和 Notion 笔记功能。

## 功能特性

### 1. LeetCode 题解
- 收录 40+ 道 LeetCode 算法题解
- 支持代码高亮显示
- 题解存放在 `src/leetCode/` 目录

### 2. Notion 笔记
- 内嵌 Notion 页面
- 专注阅读和记录

## 技术栈

- Vue 3
- Vue Router 4
- Highlight.js（代码高亮）
- Vue CLI

## 项目设置

```bash
pnpm install
```

### 开发环境运行

```bash
pnpm run serve
```

### 生产环境构建

```bash
pnpm run build
```

### 代码检查与修复

```bash
pnpm run lint
```

## 目录结构

```
death-note/
├── src/
│   ├── assets/          # 静态资源
│   ├── components/      # 组件
│   ├── leetCode/        # LeetCode 题解
│   ├── notion/          # Notion 相关组件
│   ├── router/          # 路由配置
│   ├── views/           # 页面视图
│   ├── App.vue          # 根组件
│   └── main.js          # 入口文件
├── public/              # 公共资源
├── package.json
└── vue.config.js
```

## 自定义配置

详见 [Vue CLI 配置参考](https://cli.vuejs.org/config/)。
