# Workflow 入口契约

`entry_contract.json` 是 `lgwf-wf-tools` 内部 workflow 的机器可读入口事实源。`AGENTS.md` 负责解释业务纪律，`registry.json` 负责路由，入口字段、输入示例和 auto-human 策略以契约为准。

## 必填字段

- `id`：必须等于 `registry.json` 中的 workflow id。
- `kind`：`lgwf` 或 `tool-workflow`。
- `version`：当前固定为 `1`。
- `input_mode`：`empty_then_approval`、`input_json_required`、`tool_args` 或 `no_input`。
- `input_schema`：JSON object schema，包含 `type`、`properties`、`required` 和 `example`。
- `input_file_policy`：PowerShell 下默认使用 UTF-8 no BOM `--input-json-file`。
- `auto_human_policy`：`allowed`、`conditional`、`forbidden` 或 `not_applicable`。
- `target_scope`：目标路径字段、默认推导规则和允许写入范围。
- `state_boundary`：运行状态、报告和目标写入边界。
- `outputs`：最终摘要、handoff input 和主要报告路径。
- `resume_policy`：固定 work dir 下 continue、resume、rerun 的处理原则。

## input_mode

- `empty_then_approval`：启动输入为空对象，目标信息由 workflow 内 human gate 收集。
- `input_json_required`：启动时必须提供 JSON object。
- `tool_args`：脚本型 workflow 使用 CLI 参数，不走 LGWF `--input-json`。
- `no_input`：无需输入。

## auto_human_policy

- `allowed`：facade 可在用户显式要求时传递 `--auto-human`。
- `conditional`：只有目标范围已经明确授权时允许传递 `--auto-human`。
- `forbidden`：不得自动通过 human gate。
- `not_applicable`：tool workflow 不走 LGWF human gate。

`--auto-human` 不覆盖 handoff、`agent_loop waiting_human` 或 `subgraph.react on_max`。

## 推荐统一输入模型

```json
{
  "request": {
    "objective": "用户目标",
    "target": {
      "workflow_lgwf": "D:/example/workflow.lgwf",
      "package_root": "D:/example",
      "allowed_dirs": ["D:/example"]
    },
    "options": {}
  }
}
```

第一版契约允许保留 legacy input shape。后续如果迁移到统一模型，workflow 入口应先把 `request.*` 映射为现有 state 字段，再保持下游节点不变。
