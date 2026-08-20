# 提交信息规范

提交信息采用以下格式：

```text
<类型>(可选范围): <简短描述>
```

示例：

```text
feat(editor): add markdown preview
fix(router): preserve the current note on navigation
docs: update local development instructions
```

允许的类型：`feat`、`fix`、`docs`、`dx`、`style`、`refactor`、`perf`、`test`、`workflow`、`build`、`ci`、`chore`、`types`、`wip`、`release`。

标题描述不能为空，最长 72 个字符。破坏性变更可以在类型或范围后添加 `!`。
