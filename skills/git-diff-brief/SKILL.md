---
name: git-diff-brief
description: 用于读取指定 Git 仓库的当前变更上下文，生成中文 Markdown 变更摘要和建议 commit message，并在人工确认后可选执行 stage/commit。Use when Codex needs a concise Chinese brief of worktree git diff, latest commit, key changed files, risks, suggested validation commands, and optional human-approved git add/commit through the bundled LGWF workflow.
---

# Git Diff Brief

本 skill 用于通过内置 LGWF workflow 读取 Git 仓库变更上下文，生成可直接交付的中文 Markdown 摘要和建议 commit message。默认不执行 Git 写操作；只有最终人工确认明确选择 `stage` 或 `commit` 时，才会执行对应的 `git add` 或 `git commit`。

## 使用边界

- package root：`skills/git-diff-brief`
- workflow root：`wf/`
- workflow 入口：`wf/workflow.lgwf`
- work dir：`ws/`
- 运行状态目录：`ws/.lgwf`

只把运行状态写入 `ws/.lgwf`。不要在 package 根目录写入 `.lgwf`，不要把绝对路径或 `..` 写入 workflow 资源路径。

## 快速流程

1. 先阅读本目录的 `AGENTS.md`，确认路径、状态和 workflow 分层约束。
2. 明确用户要摘要的 Git 仓库路径；如果未指定，默认使用当前工作区仓库。
3. 需要启动本 skill 自带 workflow 时，必须通过已注册的 `lgwf-wf-tools` 调用 `scripts/run_skill_workflow.py`，并把仓库路径和摘要范围作为输入交给该流程处理。
4. 摘要输出时只展示高信号内容：变更概览、关键文件、风险点、建议验证命令、建议 commit message 和未确认事项。
5. 若用户要求 stage/commit，必须在最终审批 JSON 中明确 `commit_action`，并保持默认安全行为为 `none`。
6. 面向用户的交互运行不得传入 `skip_delivery_review=true`；该开关只允许无人值守摘要生成并且 `delivery_action=none`。
7. workflow 已结束后，用户单独回复 `1`、`2`、`3`、`4` 或 `5` 不得被解释为 Git 操作；应重新运行 workflow 或要求用户明确给出新的命令和作用域。

## 运行入口

在仓库根目录执行：

```powershell
python skills\lgwf-wf-tools\scripts\run_skill_workflow.py --workflow-lgwf skills\git-diff-brief\wf\workflow.lgwf --work-dir skills\git-diff-brief\ws --input-json "{}" --background
```

该命令由 `lgwf-wf-tools` 的代理脚本调用本 facade 内置的 `lgwf.py run`，外部 skill 不需要知道 bundled `lgwf.py` 的具体路径。需要传入 `repo_path`、`summary_scope` 等业务输入时，应先准备 UTF-8 JSON 输入，再通过 `--input-json` 或 `--input-json-file` 传入。

## 最小验证

```powershell
python -m unittest discover skills\git-diff-brief\tests
python -m compileall -q skills\git-diff-brief
```
