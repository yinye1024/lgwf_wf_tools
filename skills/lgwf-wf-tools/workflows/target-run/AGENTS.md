# Target Run Workflow

本目录是 `lgwf-wf-tools` facade 下的内部 `tool-workflow`，职责是处理用户显式要求直启目标 LGWF workflow 的场景。它不是 LGWF runtime workflow，不包含固定 `workflow.lgwf`，不得作为独立 Codex skill 注册。

## 共用规则

执行本 workflow 前必须读取：

- `../01-share/AGENTS.md`
- `../01-share/module-contract.md`
- `../01-share/registry-contract.md`
- `../01-share/tool-workflow.md`
- `../01-share/lgwf-dispatch.md`
- `../01-share/lgwf-monitor.md`
- `../01-share/approval.md`
- `../01-share/artifacts.md`
- `../../docs/target-run.md`

模块类型：`tool_workflow`。本模块的入口、依赖、状态边界、产物、验证和禁止事项以本文件后续章节和 `../../docs/target-run.md` 为准。

## 触发规则

只有用户明确使用以下形式时选择本 workflow：

- `/lgwf-wf-tools run <path>`
- `/lgwf-wf-tools target-run <path>`
- `/lgwf-wf-tools --target-workflow <path>`

自然语言中的“修复”“优化”“生成测试”“规划”“检查 prompt”等请求，即使包含 workflow 目录或 `workflow.lgwf` 路径，也不要选择本 workflow，应回到根 `AGENTS.md` 重新路由。

## 执行边界

- 目标路径解析、已有运行目录处理、启动和监控规则以 `../../docs/target-run.md` 为准。
- 本 workflow 使用 facade 内置 `vendor/lgwf-client-assist/scripts/lgwf.py` 启动目标 workflow。
- 解析失败时报告失败原因，不回退到其他内部 workflow。
- 如果目标 `work_dir/.lgwf` 已存在，必须让用户选择 `continue`、`resume` 或 `rerun`，不要直接启动第二个 run。
