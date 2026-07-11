# Entry Contract 契约

`entry_contract.json` 是 registry workflow 的机器可读入口说明。

## 必备字段

- `id`：必须与 registry 条目一致。
- `kind`：必须与 registry 条目一致。
- `version`：当前模板使用 `1`。
- `input_mode`：`empty_then_approval`、`input_json_required`、`tool_args` 或 `no_input`。
- `input_schema`：JSON object schema，包含 `properties`、`required` 和 `example`。
- `input_file_policy`：说明输入文件策略。
- `auto_human_policy`：`allowed`、`conditional`、`forbidden` 或 `not_applicable`。
- `target_scope`：读取和写入范围。
- `state_boundary`：运行状态边界。
- `outputs`：主要产物。
- `resume_policy`：恢复或重跑规则。

## `lgwf` 额外字段

- `workflow_lgwf`
- `work_dir`

这两个字段必须与 registry 条目一致。

## `tool-workflow` 额外字段

- `entry`

该字段必须与 registry 条目一致。
