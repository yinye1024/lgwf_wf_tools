# git-diff-brief

`git-diff-brief` 是一个内部 LGWF workflow package，用于读取指定 Git 仓库的当前变更上下文，生成可直接阅读的中文 Markdown 变更摘要。

## 目标

- 接收仓库目录与最小摘要范围。
- 采集工作区 `git diff`、最近一次提交信息和关键变更文件。
- 生成包含变更概览、关键文件、风险点和建议验证命令的中文 Markdown 草稿。
- 在最终交付前保留阶段内人工确认点。

## 目录边界

- package root：`plugins/team-skills/skills/git-diff-brief`
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

根 `wf/workflow.lgwf` 只负责按顺序串联这四个第一层子 workflow。每个阶段目录都自包含自己的 `workflow.lgwf`、`agents/`、`scripts/` 和 `resources/`。

## 当前初稿说明

- 第一阶段会规范化仓库输入并通过阶段内确认节点收束范围歧义。
- 第二阶段以 Python 脚本读取 Git 事实，并输出可追踪的结构化上下文。
- 第三阶段把结构化事实转成中文 Markdown 草稿和验证建议。
- 第四阶段负责展示、确认和整理最终输出索引。

当前初稿刻意保留以下待确认项：

- 是否支持分支对比、提交范围选择或自定义输出路径。
- 空 diff、无提交历史和超大 diff 的最终产品语义。
- 用户要求修订时的精细回流策略与默认落盘策略。

## 最小验证

从仓库根目录运行：

```powershell
python -m unittest discover plugins\team-skills\skills\git-diff-brief\tests
python -m compileall -q plugins\team-skills\skills\git-diff-brief
```

如环境已安装 `lgwf_dsl`，可追加：

```powershell
python -m lgwf_dsl.cli audit plugins\team-skills\skills\git-diff-brief\wf\workflow.lgwf
```
