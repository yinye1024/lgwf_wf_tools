---
name: git-diff-brief
description: 用于读取指定 Git 仓库的当前变更上下文并生成中文 Markdown 变更摘要。Use when Codex needs a concise Chinese brief of worktree git diff, latest commit, key changed files, risks, and suggested validation commands through the bundled LGWF workflow.
---

# Git Diff Brief

本 skill 用于通过内置 LGWF workflow 读取 Git 仓库变更上下文，并生成可直接交付的中文 Markdown 摘要。

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
4. 摘要输出时只展示高信号内容：变更概览、关键文件、风险点、建议验证命令和未确认事项。

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
