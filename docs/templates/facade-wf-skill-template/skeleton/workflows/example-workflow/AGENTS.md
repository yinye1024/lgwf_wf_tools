# example-workflow 指引

本目录是 facade 内部的示例 `lgwf_workflow_package`，不是独立 Codex skill。它用于展示 registry 条目、`entry_contract.json`、`wf/workflow.lgwf` 和 `ws/.lgwf/` 状态边界。

## 模块契约

- 模块类型：`lgwf_workflow_package`。
- registry id：`example-workflow`。
- workflow 入口：`workflows/example-workflow/wf/workflow.lgwf`。
- work dir：`workflows/example-workflow/ws`。
- 入口字段和输入示例以 `entry_contract.json` 为准。

## 依赖

- 依赖 facade runner。
- 依赖目标仓库提供 LGWF runtime。
- 依赖 `workflows/01-share/` 的共享规则。

## 状态边界

运行状态只写入 `workflows/example-workflow/ws/.lgwf/`。不要把 `.lgwf/` 写入 `wf/` 源码目录。

## 产物

- `.lgwf/example_summary.json`
- `state.example_workflow.summary`

## 验证

```powershell
python scripts\validate_registry.py
```

## 禁止事项

- 不要把本目录注册为独立 Codex skill。
- 不要把示例 workflow 保留在正式业务 registry 中。
- 不要自动审批或跳过人工确认模板。
