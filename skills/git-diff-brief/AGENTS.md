# git-diff-brief 协作指引

## 包定位

- 当前目录是 `internal_workflow_package`，真实 workflow root 仅在 `wf/`。
- 根目录提供 `SKILL.md` 作为 Codex skill 入口，但不生成可运行的根 `workflow.lgwf`。
- 本包用于读取 Git 仓库变更上下文并生成中文 Markdown 变更摘要初稿。

## 路径与状态边界

- 所有 workflow 资源路径必须保持包内相对路径。
- 不得在源码树根目录写入 `.lgwf`、绝对路径或 `..`。
- 本包运行时默认使用同级 `ws/` 作为 work dir；运行状态只允许写入 `ws/.lgwf`。
- 启动本包 workflow 时，必须通过已注册的 `lgwf-wf-tools` 调用 `scripts/run_skill_workflow.py`，并显式传入 `--workflow-lgwf skills/git-diff-brief/wf/workflow.lgwf` 与 `--work-dir skills/git-diff-brief/ws`；不要直接调用 `vendor/lgwf-client-assist/scripts/lgwf.py run`。

## workflow 结构

- `wf/workflow.lgwf` 只编排四个第一层业务阶段子 workflow。
- `wf/<stage>/workflow.lgwf` 承载阶段内具体节点、确认点和脚本调用。
- 禁止创建 `wf/<stage>/<substage>/workflow.lgwf`。

## 当前初稿范围

- 已补齐请求范围对齐、Git 上下文采集、摘要生成、结果复核与交付四个阶段的最小目录与文件。
- 允许保留占位 prompt、待确认契约和最小脚本实现。
- 不包含 `lgwf-wf-prompt-fix`、`lgwf-wf-tools` 集成、自动修复和端到端成功保证。
