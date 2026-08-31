# Git 切换分支时如何暂存当前改动

# Git 切换分支时如何暂存当前改动

> 开发过程中经常遇到：工作到一半需要切分支处理紧急任务，但当前改动还不能提交。Git 提供了多种暂存方案。
> 

---

## 一、git stash（最常用）

### 1.1 基本操作

```bash
# 暂存所有改动（包括 staged 和 unstaged）
git stash

# 或带描述信息
git stash push -m "临时保存：用户模块开发中"
```

```bash
# 查看 stash 列表
git stash list
# 输出示例：
# stash@{0}: On main: 临时保存：用户模块开发中
# stash@{1}: WIP on feature: 845f3a2 完成登录页面
```

```bash
# 恢复最近的 stash（保留 stash 记录）
git stash apply

# 恢复并删除 stash 记录
git stash pop
```

### 1.2 恢复指定的 stash

```bash
# 恢复特定 stash（从 stash list 中查看编号）
git stash apply stash@{1}

# 或使用数字索引
git stash apply 1
```

### 1.3 查看/删除/清空 stash

```bash
# 查看 stash 中的具体改动
git stash show stash@{0}        # 简要概览
git stash show -p stash@{0}     # 完整 diff

# 删除某个 stash
git stash drop stash@{0}

# 清空所有 stash
git stash clear
```

---

## 二、stash 进阶用法

### 2.1 只暂存部分文件

```bash
# 只 stash 指定文件
git stash push src/utils.ts src/api/user.ts -m "暂存指定文件"

# 交互式选择（逐个文件确认）
git stash push -p
# 会依次询问每个 hunk：y/n/q/a/d/s/e/?
# y: stash this hunk / n: skip / s: split / e: edit
```

### 2.2 包含未跟踪的文件

```bash
# stash 默认不包含 untracked 文件，加 -u
git stash push -u -m "包含新建但未 add 的文件"
# 等效于
git stash push --include-untracked

# 包含所有文件（包括 ignored）
git stash push -a -m "包含 .gitignore 的文件"
# 等效于
git stash push --all
```

### 2.3 只暂存 unstaged 改动

```bash
# 保留已 staged 的改动，只 stash 未 staged 的
git stash push --keep-index

# 常用场景：部分信息已暂存准备提交，临时需要切分支
git add -p          # 选择性暂存要保留的改动
git stash push --keep-index -m "只暂存未 staged 的改动"
```

---

## 三、git worktree（进阶方案）

> stash 方案不是唯一选择。对于大型项目，频繁 stash/pop 效率不高，`git worktree` 可以让你同时 checkout 多个分支到不同目录。
> 

### 3.1 基本用法

```bash
# 创建一个新 worktree，同时切换到 feature 分支
git worktree add ../project-feature feature/urgent-fix

# 列出所有 worktree
git worktree list
# /path/to/project           abc123 [main]
# /path/to/project-feature   def456 [feature/urgent-fix]

# 使用完后删除
git worktree remove ../project-feature
git worktree prune   # 清理已删除的 worktree 记录
```

### 3.2 worktree vs stash 选择

| 场景 | 推荐方案 |
| --- | --- |
| 临时切分支几分钟 | `git stash`  • `git stash pop` |
| 需要同时维护两个分支 | `git worktree` |
| 当前改动太多，stash pop 容易冲突 | `git worktree` |
| 需要在另一个目录跑不同分支的测试 | `git worktree` |

---

## 四、临时提交再撤销（备选方案）

> 不习惯 stash 时也可以用轻量级 WIP 提交，切回后再 reset。
> 

### 4.1 WIP 提交法

```bash
# 先暂存并做一个 WIP 提交
git add .
git commit -m "WIP: 临时保存，稍后恢复"

# 切换到目标分支工作
git checkout other-branch
# ... 完成紧急任务 ...

# 回到原分支，撤销 WIP 提交但保留改动
git checkout original-branch
git reset HEAD~1     # 撤销提交，回到未提交状态（默认 --mixed）
```

### 4.2 三种 reset 模式

| 模式 | 工作区改动 | 暂存区 | HEAD |
| --- | --- | --- | --- |
| `--soft` | ✅ 保留 | ✅ 保留（新状态） | ⬅ 回退 |
| `--mixed`（默认） | ✅ 保留 | 🔄 清空（回退前状态回到工作区） | ⬅ 回退 |
| `--hard` | ❌ 丢弃 | ❌ 清空 | ⬅ 回退 |

> ⚠️ `git reset --hard` 会丢弃所有未提交的改动，**慎用！**
> 

---

## 五、常见场景速查

### 5.1 场景一：紧急修 bug，当前改动需要暂存

```bash
git stash push -m "当前工作暂存"
git checkout hotfix-branch
# ... 修 bug，提交 ...
git checkout original-branch
git stash pop
```

### 5.2 场景二：stash pop 后发生冲突

```bash
# pop 时冲突，stash 不会自动删除
# 解决冲突后手动删除
git stash drop stash@{0}

# 或者先 apply（不会删除 stash），确认无误再 drop
git stash apply stash@{0}
# ... 解决冲突 ...
git stash drop stash@{0}
```

### 5.3 场景三：从 stash 创建新分支测试

```bash
# 将 stash 应用到新分支并切换
git stash branch test-stash-branch stash@{0}
# 这会在 base commit 上创建新分支，应用 stash，然后 drop stash
```

### 5.4 场景四：多项目同时开发

```bash
# 使用 worktree 避免频繁切换
cd /path/to/main-project
git worktree add ../project-frontend frontend-dev
git worktree add ../project-backend backend-dev

# 三个目录同时工作，互不影响
# ../project-frontend   对应 frontend-dev 分支
# ../project-backend    对应 backend-dev 分支
```

---

## 六、快速参考卡片

```bash
# -------------------- 暂存 --------------------
git stash                           # 暂存所有改动
git stash push -m "描述"           # 带描述暂存
git stash push -u                   # 包含未跟踪文件
git stash push -p                   # 交互式选择暂存
git stash push --keep-index         # 保留 staged（已经 add 的）

# -------------------- 查看 --------------------
git stash list                      # 列出所有 stash
git stash show stash@{0}            # 查看简要内容
git stash show -p stash@{0}         # 查看完整 diff

# -------------------- 恢复 --------------------
git stash pop                       # 恢复最近 stash 并删除记录
git stash apply                     # 恢复最近 stash 保留记录
git stash pop stash@{1}             # 恢复指定 stash
git stash branch <分支名> stash@{0} # 在新分支恢复 stash

# -------------------- 清理 --------------------
git stash drop stash@{0}            # 删除指定 stash
git stash clear                     # 清空所有 stash

# -------------------- worktree --------------------
git worktree add ../dir <分支>      # 创建新 worktree
git worktree list                   # 列出所有 worktree
git worktree remove ../dir          # 移除 worktree
```

---

## 七、总结

| 方案 | 适用场景 | 优点 | 缺点 |
| --- | --- | --- | --- |
| **git stash** | 临时暂存，几分钟到几小时 | 快速、简单、轻量 | pop 时可能冲突，忘了会堆积 |
| **git worktree** | 长期并行开发，多分支同时活跃 | 互不影响，真正并行 | 占用磁盘空间，需熟悉新命令 |
| **WIP 临时提交** | 不习惯 stash，想保留提交历史 | 简单直观，有 commit SHA | 污染提交历史（适合个人分支） |

> 💡 **建议**：日常开发首选 `git stash`。当发现 stash 列表超过 3 条，或需要在两个分支间来回切换时，考虑切换到 `git worktree`。
> 

## 八、WebStorm 图形化操作

> WebStorm 内置了完整的 Git Stash 图形界面，无需记忆命令，日常操作更直观。
> 

### 8.1 暂存改动（Stash）

**方法一：顶部菜单**

1. `VCS` → `Git` → `Stash Changes...`
2. 弹窗中填写：
    - `Message`：填写描述（对应 `git stash push -m "..."`）
    - ✅ `Keep staged changes`：只 stash 未 staged 的（`--keep-index`）
    - ✅ `Include untracked files`：包含未跟踪文件（`-u`）
3. 点击 `Create Stash`

**方法二：右键菜单**

- 编辑器或 Project 视图中右键 → `Git` → `Stash Changes...`

**方法三：Commit 工具窗口**

- 打开 Commit 工具窗口（`Alt+0` / `Cmd+0`）
- 点击 Diff 面板上方的 `Stash` 按钮（📦 图标）

### 8.2 恢复改动（Unstash）

1. 顶部菜单 → `VCS` → `Git` → `Unstash Changes...`
2. 在 stash 列表中选择要恢复的条目
3. 选择操作：
    - `Apply Stash`：恢复但保留 stash 记录（对应 `git stash apply`）
    - `Pop Stash`：恢复并删除 stash 记录（对应 `git stash pop`）

> 💡 stash 列表展示 Message 内容 — stash 时写清楚描述很重要！
> 

### 8.3 查看与删除 stash

**查看内容**：

1. `VCS` → `Git` → `Unstash Changes...`
2. 选中某个 stash → 下方显示该 stash 包含的文件列表
3. 双击文件可查看 diff 视图

**删除操作**：

- 在 Unstash 窗口中选中 stash → 点击 `Drop` → 删除单条
- 点击 `Clear All` → 清空所有 stash

### 8.4 图形化 vs 命令行操作速查

| 操作 | WebStorm 菜单位置 | 对应命令 |
| --- | --- | --- |
| 暂存改动 | VCS → Git → Stash Changes | `git stash push -m "..."` |
| 恢复（保留记录） | VCS → Git → Unstash → Apply Stash | `git stash apply` |
| 恢复（删除记录） | VCS → Git → Unstash → Pop Stash | `git stash pop` |
| 查看 stash 内容 | Unstash 窗口 → 选中 → 双击文件 | `git stash show -p` |
| 删除单条 stash | Unstash 窗口 → Drop | `git stash drop` |
| 清空所有 stash | Unstash 窗口 → Clear All | `git stash clear` |

### 8.5 图形化优势总结

```
┌──────────────────────────────────────────────────────┐
│            WebStorm 图形化操作优势                   │
├──────────────────────────────────────────────────────┤
│  ✅ 可视化查看每个 stash 包含哪些文件               │
│  ✅ 双击文件直接看 diff，不用 memorizing 命令       │
│  ✅ Message 字段强制填写，不容易忘记 stash 用途      │
│  ✅ 勾选框操作比记参数更简单                        │
│  ✅ 列表展示，不容易误 pop 或 drop                 │
│  ✅ 可同时看到多个 stash，一目了然                  │
├──────────────────────────────────────────────────────┤
│           命令行优势                                 │
│  ✅ 熟练后速度更快                                  │
│  ✅ 支持交互式 stash -p（图形界面不支持逐 hunk 选）  │
│  ✅ 脚本自动化                                      │
└──────────────────────────────────────────────────────┘
```

> 🔑 **最佳实践**：日常操作使用 WebStorm 图形界面（直观、不易出错）；需要精细控制（如 `-p` 交互式选择）时切换到命令行。
>