# git-diff-brief

`git-diff-brief` 是一个内部 LGWF workflow package，用于读取指定 Git 仓库的当前变更上下文，生成可直接阅读的中文 Markdown 变更摘要，并给出可人工确认的建议提交信息。

## 目标

- 接收仓库目录与最小摘要范围。
- 采集工作区 `git diff`、最近一次提交信息和关键变更文件。
- 生成包含变更概览、关键文件、风险点和建议验证命令的中文 Markdown 草稿。
- 生成 Conventional Commits 风格的建议 `commit_message` 及中文依据说明。
- 在最终交付前保留阶段内人工确认点。
- 仅在最终审批显式选择时执行 `git add` 或 `git commit`；默认不执行任何 Git 写操作。

## 目录边界

- package root：`skills/git-diff-brief`
- workflow root：`wf/`
- workflow 入口：`wf/workflow.lgwf`
- work dir：`ws/`
- 运行状态目录：`ws/.lgwf`

根目录提供 `SKILL.md` 作为 Codex skill 入口，但不生成可运行的根 `workflow.lgwf`。运行状态不得写入 package 根目录 `.lgwf`。

## 阶段结构

1. `01_request_scope_alignment`
2. `02_git_context_collection`
3. `03_brief_synthesis`
4. `04_result_review_and_delivery`
5. `05_git_commit`

第四阶段负责展示摘要、确认交付决策并生成提交计划；第五阶段读取提交计划并执行或跳过 Git 写操作。

最终审批支持：

- `commit_action=none`：默认值，只整理摘要和提交建议。
- `commit_action=stage`：执行 `git add -- <relative_scope>`。
- `commit_action=commit`：执行 `git add -- <relative_scope>` 后执行 `git commit -m <commit_message>`。

`stage` 和 `commit` 只使用 Git 采集产物中的 `repo_path` 与 `relative_scope`，不接受人工输入任意 pathspec。

根 `wf/workflow.lgwf` 只负责按顺序串联这四个第一层子 workflow。每个阶段目录都自包含自己的 `workflow.lgwf`、`agents/`、`scripts/` 和 `resources/`。

## 当前初稿说明

- 第一阶段会规范化仓库输入并通过阶段内确认节点收束范围歧义。
- 第二阶段以 Python 脚本读取 Git 事实，并输出可追踪的结构化上下文。
- 第三阶段把结构化事实转成中文 Markdown 草稿和验证建议。
- 第四阶段负责展示、确认和整理最终输出索引，并生成提交计划。
- 第五阶段负责读取提交计划，并在人工明确确认后可选执行 stage/commit。

当前初稿刻意保留以下待确认项：

- 是否支持分支对比、提交范围选择或自定义输出路径。
- 空 diff、无提交历史和超大 diff 的最终产品语义。
- 用户要求修订时的精细回流策略与默认落盘策略。

## 最小验证

从仓库根目录运行：

```powershell
python -m unittest discover skills\git-diff-brief\tests
python -m compileall -q skills\git-diff-brief
```

如环境已安装 `lgwf_dsl`，可追加：

```powershell
python -m lgwf_dsl.cli audit skills\git-diff-brief\wf\workflow.lgwf
```
